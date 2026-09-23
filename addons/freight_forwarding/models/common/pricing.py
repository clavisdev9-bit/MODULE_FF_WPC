"""FF-81: Charge Table (product.pricelist header + product.pricelist.item
rules) and Cost Table (product.supplierinfo, flat) -- extend the native
Sales Pricelist / Vendor Pricelist models with the Freight Forwarding
fields instead of building a custom header/line model.

Architecture:
- Charge Table = native `product.pricelist` header (carries `ff_type`,
  hidden, used only for Air/Sea action domain/context, plus the additive
  "Freight Forwarding" header fields from the Jira ticket) with native
  `product.pricelist.item` rules (carry the FF pricing fields).
- Cost Table = native flat `product.supplierinfo`, one record per
  vendor/product; NOT symmetrical with Charge Table, so it carries both
  `ff_type` and the FF pricing fields on the same (flat) record.

`freight.pricing.mixin` only holds what both `product.pricelist.item` and
`product.supplierinfo` share: the FF pricing fields and their defaulting
behaviour from the selected Charge Code (product.template).
"""
from odoo import api, fields, models

from ..master_data.acct.charge_code import CHARGE_UNIT_SELECTION

FF_PRICING_TYPE_SELECTION = [
    ('air', 'Air'),
    ('sea', 'Sea'),
]

FF_PRICING_CARGO_SELECTION = [
    ('FCL', 'FCL'),
    ('LCL', 'LCL'),
]

# FF-81: Valid Flag / Standard Charge Flag / Freight Collect are storage-only
# Y/N selections -- no business behaviour (see Jira "Field only" list).
FF_YES_NO_SELECTION = [
    ('Y', 'Y'),
    ('N', 'N'),
]

# FF fields whose default comes from the Charge Code (product.template) and
# that must be refreshed whenever the Product changes, unless the caller
# explicitly supplied a value for that field in the same create/write call.
_FF_PRODUCT_SOURCE_FIELD = {
    'ff_uom_id': 'cc_uom_id',
    'ff_vat_id': 'cc_vat_id',
    'ff_charge_unit': 'cc_charge_unit',
}


class FreightPricingMixin(models.AbstractModel):
    _name = 'freight.pricing.mixin'
    _description = 'Freight Forwarding Pricing Extension (Charge/Cost Table)'

    # Cargo (FCL/LCL) is Sea-only; additive column, hidden on Air via
    # context (see action definitions below) -- never shown/required on Air.
    ff_cargo = fields.Selection(FF_PRICING_CARGO_SELECTION, string='Cargo')
    ff_uom_id = fields.Many2one('uom.uom', string='UoM')
    ff_vat_id = fields.Many2one('account.tax', string='VAT')
    ff_charge_unit = fields.Selection(CHARGE_UNIT_SELECTION, string='Charge Unit')

    def _ff_pricing_product_template(self):
        self.ensure_one()
        return self.product_tmpl_id or self.product_id.product_tmpl_id

    def _apply_ff_pricing_defaults(self, explicit_fields=()):
        """Default UoM/VAT/Charge Unit from the selected Charge Code.

        Every FF default field NOT in `explicit_fields` is (re)filled from
        the current Product, overwriting any stale value left over from a
        previously selected Product -- selecting/changing Product always
        refreshes these, the user may still override them afterwards.
        `explicit_fields` are the FF fields the caller explicitly supplied
        in the current create/write call, and are therefore left untouched.
        """
        for rec in self:
            product = rec._ff_pricing_product_template()
            if not product:
                continue
            for field_name, source_field in _FF_PRODUCT_SOURCE_FIELD.items():
                if field_name in explicit_fields:
                    continue
                rec[field_name] = product[source_field]

    @api.onchange('product_tmpl_id', 'product_id')
    def _onchange_ff_pricing_product(self):
        self._apply_ff_pricing_defaults()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list):
            explicit_fields = {f for f in _FF_PRODUCT_SOURCE_FIELD if f in vals}
            rec._apply_ff_pricing_defaults(explicit_fields=explicit_fields)
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'product_tmpl_id', 'product_id'} & set(vals):
            explicit_fields = {f for f in _FF_PRODUCT_SOURCE_FIELD if f in vals}
            self._apply_ff_pricing_defaults(explicit_fields=explicit_fields)
        return result


class ProductPricelistItemFreight(models.Model):
    """Charge Table rule."""
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'freight.pricing.mixin']


class ProductSupplierinfoFreight(models.Model):
    """Cost Table (flat -- not symmetrical with Charge Table)."""
    _name = 'product.supplierinfo'
    _inherit = ['product.supplierinfo', 'freight.pricing.mixin']

    # Not shown to the user -- only used by Air/Sea menus & actions to
    # create/filter records (see FF-81). Cost Table is flat, so the type
    # lives directly on the record (unlike Charge Table, where it lives on
    # the product.pricelist header -- see ProductPricelistFreight below).
    ff_type = fields.Selection(FF_PRICING_TYPE_SELECTION, string='Type')


class ProductPricelistFreight(models.Model):
    """Charge Table header.

    Native `name` remains the SOLE mandatory header field (Charge Table
    No.). Native `currency_id`, `company_id`, `country_group_ids` and
    `active` are unchanged. Everything below is additive/optional, grouped
    under a "Freight Forwarding" section on the native Pricelist form.
    """
    _name = 'product.pricelist'
    _inherit = ['product.pricelist']

    # Not shown to the user -- only used by Air/Sea menus & actions to
    # create/filter Charge Tables (see FF-81).
    ff_type = fields.Selection(FF_PRICING_TYPE_SELECTION, string='Type')

    # -- Common header fields (Air & Sea), all optional ---------------------
    ff_description = fields.Char(string='Description')
    ff_job_type_id = fields.Many2one('freight.job.type', string='Job Type')
    # Module is NOT independently input -- it is a straight readonly
    # reflection of the selected Job Type's Module Code (see Jira "Job
    # Type/Module: dua field berbeda ... tidak diinput independen").
    ff_module_code = fields.Char(
        related='ff_job_type_id.module_code', string='Module', readonly=True,
    )
    ff_customer_id = fields.Many2one('res.partner', string='Customer')
    ff_destination_city_id = fields.Many2one('res.city', string='Destination')

    # Field-only, no business behaviour (Jira "Field only" list) -- storage
    # only, must NOT drive `active`, pricing/rate matching, or billing.
    ff_valid_flag = fields.Selection(FF_YES_NO_SELECTION, string='Valid Flag')
    ff_standard_charge_flag = fields.Selection(FF_YES_NO_SELECTION, string='Standard Charge Flag')
    ff_transit_time = fields.Integer(string='Est. Transit Time')
    ff_frequency = fields.Char(string='Frequency')
    ff_freight_collect = fields.Selection(FF_YES_NO_SELECTION, string='Freight Collect')
    ff_note = fields.Char(string='Note')
    ff_note_code = fields.Char(string='Note Code')

    # Header validity -- see `_get_applicable_rules_domain` override below
    # for the read-time precedence rule over native line date_start/date_end.
    ff_effective_date = fields.Date(string='Effective Date')
    ff_expiry_date = fields.Date(string='Expiry Date')

    # -- Sea-specific route fields (ff_type == 'sea') ------------------------
    ff_port_of_loading_id = fields.Many2one('freight.port', string='Port of Loading')
    ff_port_of_discharge_id = fields.Many2one('freight.port', string='Port of Discharge')
    ff_via_port_id = fields.Many2one('freight.port', string='Via Port')

    # -- Air-specific route fields (ff_type == 'air') ------------------------
    ff_airport_of_origin_id = fields.Many2one('freight.airport', string='Airport of Origin/Departure')
    ff_airport_of_destination_id = fields.Many2one('freight.airport', string='Airport of Destination')
    ff_via_airport_id = fields.Many2one('freight.airport', string='Via Airport')

    # -- Header validity precedence over native line date_start/date_end ----
    # Jira "Header Validity": if the header boundary (Effective/Expiry Date)
    # is filled, it takes precedence over EVERY line's native date_start/
    # date_end for that boundary; an empty header boundary falls back to
    # each line's own native date. This is implemented purely as a read-time
    # override of the rule-matching domain -- native line Start/End Date
    # fields are never touched/copied/mutated.
    def _get_applicable_rules_domain(self, products, date, **kwargs):
        domain = super()._get_applicable_rules_domain(products, date, **kwargs)
        if not self or not (self.ff_effective_date or self.ff_expiry_date):
            return domain

        check_date = fields.Date.to_date(date) if date else fields.Date.context_today(self)
        domain = list(domain)

        if self.ff_effective_date:
            domain = self._ff_strip_date_domain_clause(domain, 'date_start')
            if check_date < self.ff_effective_date:
                # Whole Charge Table not yet effective -- no line can match.
                domain.append(('id', '=', False))

        if self.ff_expiry_date:
            domain = self._ff_strip_date_domain_clause(domain, 'date_end')
            if check_date > self.ff_expiry_date:
                # Whole Charge Table expired -- no line can match.
                domain.append(('id', '=', False))

        return domain

    @api.model
    def _ff_strip_date_domain_clause(self, domain, field_name):
        """Remove the native `'|', (field_name, '=', False), (field_name, OP, date)`
        triple for `field_name` from a domain built by
        `_get_applicable_rules_domain`, leaving every other clause intact."""
        result = []
        i = 0
        while i < len(domain):
            item = domain[i]
            if (
                item == '|'
                and i + 2 < len(domain)
                and isinstance(domain[i + 1], (tuple, list))
                and domain[i + 1][0] == field_name
            ):
                i += 3
                continue
            result.append(item)
            i += 1
        return result
