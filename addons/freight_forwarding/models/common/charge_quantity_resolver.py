"""FF-82: centralized Charge Unit -> Actual Qty resolver.

Single place that turns a Charge Code's Charge Unit + a Sea/Air Job's
operational data into an Actual Qty, so the formula never has to be
duplicated in a view or scattered across invoice methods. Minimum Billable
Qty (Charge Code) is applied by the caller (sale.order.line), not here --
this resolver only ever returns operational Actual Qty.

Returns `None` whenever the Charge Unit has no confirmed business formula
yet (see `_TBD_CHARGE_UNITS`) or the Job/business type doesn't support it --
callers must treat `None` as "leave quantity untouched", never invent 0.
"""
import math

from odoo import models

# FF-82 section 6: Charge Units without a confirmed business formula yet.
# Must never be given a formula here -- keep them out of the dispatch below.
_TBD_CHARGE_UNITS = {
    'subhouse_bl',
    'block_4m3',
    'block_3m3',
    'invoice_charge_weight',
    'ccfee',
}

_SEA_CONTAINER_SIZE_CODE = {
    '20ft': '20FT',
    '40ft': '40FT',
    '45ft': '45FT',
}


class FreightChargeQuantityResolver(models.AbstractModel):
    _name = 'freight.charge.quantity.resolver'
    _description = 'FF-82 Charge Unit to Actual Qty Resolver'

    def _ff_resolve_actual_qty(self, job, charge_unit):
        """Return the Actual Qty (float) for `charge_unit` given a single
        Sea (`freight.sea.job`) or Air (`freight.air.job`) Job record, or
        `None` when the unit/job combination has no confirmed formula."""
        if not job or not charge_unit or charge_unit in _TBD_CHARGE_UNITS:
            return None
        if job._name == 'freight.air.job':
            return self._ff_resolve_air_qty(job, charge_unit)
        if job._name == 'freight.sea.job':
            return self._ff_resolve_sea_qty(job, charge_unit)
        return None

    # -- Air ---------------------------------------------------------------
    def _ff_resolve_air_qty(self, job, charge_unit):
        if charge_unit == 'rev_ton_cw':
            # FF-82 section 3: canonical for both Export and Import --
            # resolver never reads volumetric_weight/import_volumetric_weight
            # directly.
            return job.charge_weight
        if charge_unit == 'rev_ton_rnd':
            return math.ceil(job.charge_weight or 0.0)
        if charge_unit == 'shipment':
            return 1.0
        if charge_unit == 'house':
            return self._ff_resolve_house_qty(job)
        if charge_unit == 'volume':
            if job.freight_type == 'export':
                return job.total_m3
            return None  # Air Import: no confirmed operational volume source
        if charge_unit == 'weight':
            return job.gross_weight
        if charge_unit == 'pcs':
            return job.total_pcs if job.freight_type == 'export' else job.pcs
        # Container units are Sea-only.
        return None

    # -- Sea -----------------------------------------------------------
    def _ff_resolve_sea_qty(self, job, charge_unit):
        cargo_lines = job.cargo_info_ids
        if charge_unit in ('20ft', '40ft', '45ft', 'total_container'):
            return self._ff_sea_container_count(cargo_lines, charge_unit)
        if charge_unit == 'rev_ton_cw':
            return self._ff_sea_rev_ton(cargo_lines)
        if charge_unit == 'rev_ton_rnd':
            return math.ceil(self._ff_sea_rev_ton(cargo_lines))
        if charge_unit == 'shipment':
            return 1.0
        if charge_unit == 'house':
            return self._ff_resolve_house_qty(job)
        if charge_unit == 'volume':
            return self._ff_sea_total_cbm(cargo_lines)
        if charge_unit == 'weight':
            return sum(cargo_lines.mapped('gross_weight'))
        if charge_unit == 'pcs':
            return sum(cargo_lines.mapped('quantity'))
        return None

    def _ff_sea_container_count(self, cargo_lines, charge_unit):
        """FF-82 section 4: distinct `container_no`, never `quantity` or line
        count -- the same container repeated on several cargo lines still
        counts once."""
        lines = cargo_lines.filtered(lambda line: line.container_no)
        if charge_unit == 'total_container':
            return float(len(set(lines.mapped('container_no'))))
        target_size = _SEA_CONTAINER_SIZE_CODE[charge_unit]
        matched = lines.filtered(
            lambda line: (line.container_type_id.size_code or '').strip().upper() == target_size
        )
        return float(len(set(matched.mapped('container_no'))))

    def _ff_sea_total_cbm(self, cargo_lines):
        """FF-82 section 4: aggregate CBM across cargo lines, per-line source
        priority total_volume -> volume*quantity -> quantity*L*W*H (cm3)."""
        total = 0.0
        for line in cargo_lines:
            if line.total_volume:
                total += line.total_volume
            elif line.volume:
                total += line.volume * (line.quantity or 1)
            elif line.length and line.width and line.height:
                total += (line.length * line.width * line.height / 1_000_000.0) * (line.quantity or 1)
        return total

    def _ff_sea_rev_ton(self, cargo_lines):
        """FF-82 section 4: temporary formula pending Pak Asen re-confirmation
        -- do not change without new requirement."""
        total_dimension_cm3 = self._ff_sea_total_cbm(cargo_lines) * 1_000_000.0
        volumetric_weight = total_dimension_cm3 / 6000.0
        total_gross_weight = sum(cargo_lines.mapped('gross_weight'))
        return max(volumetric_weight, total_gross_weight)

    # -- Shared --------------------------------------------------------
    def _ff_resolve_house_qty(self, job):
        if job._name == 'freight.sea.job':
            if job.record_level == 'house':
                return 1.0
            if job.record_level == 'master':
                return float(len(job.house_job_ids.filtered(lambda h: h.state != 'cancelled')))
            return 0.0
        if job._name == 'freight.air.job':
            if job.shipment_type == 'house':
                return 1.0
            if job.shipment_type == 'master':
                return float(len(job.house_job_ids.filtered(lambda h: h.state != 'cancelled')))
            return 0.0  # Air Direct
        return None
