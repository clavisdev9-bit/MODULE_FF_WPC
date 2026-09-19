from odoo import api, fields, models
from odoo.exceptions import UserError


class AirAddToMasterWizard(models.TransientModel):
    """FF-75: wizard 'Add to Master' -- Quotation Export tambahan (Q2, Q3, ...)
    digabungkan ke Master AWB existing tanpa membuat Booking baru. House AWB
    baru dibuat dari Quotation aktif dan langsung ter-gabung (master_job_id)
    ke Master yang dipilih di sini."""

    _name = "freight.air.add.to.master.wizard"
    _description = "Air Add to Master Wizard"

    quotation_id = fields.Many2one(
        "sale.order",
        string="Quotation",
        required=True,
        readonly=True,
    )
    freight_type = fields.Selection(
        [("import", "Import"), ("export", "Export")],
        string="Type",
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
    )
    master_job_id = fields.Many2one(
        "freight.air.job",
        string="Master Job",
        required=True,
        domain="[('shipment_type', '=', 'master'), ('freight_type', '=', freight_type),"
               " ('company_id', '=', company_id), ('state', 'not in', ['closed', 'cancelled'])]",
        help="Master harus Freight Type & Company yang sama dengan Quotation, "
             "berstatus aktif (bukan Closed/Cancelled).",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        quotation_id = self.env.context.get("default_quotation_id")
        if quotation_id:
            quotation = self.env["sale.order"].browse(quotation_id)
            res["quotation_id"] = quotation.id
            res["freight_type"] = quotation.freight_type
            res["company_id"] = quotation.company_id.id
        return res

    def action_add_to_master(self):
        """Section G: validasi ulang di backend -- domain wizard hanya untuk
        UX, RPC/API lain yang menulis master_job_id langsung harus tetap
        ditolak kalau kandidat tidak valid."""
        self.ensure_one()
        master = self.master_job_id
        if master.shipment_type != "master":
            raise UserError("Job yang dipilih harus berupa Master Job.")
        if master.freight_type != self.quotation_id.freight_type:
            raise UserError("Master harus punya Type (Import/Export) yang sama dengan Quotation.")
        if master.company_id != self.quotation_id.company_id:
            raise UserError("Master harus berada di Company yang sama dengan Quotation.")
        if master.state in ("closed", "cancelled"):
            raise UserError("Master (%s) sudah %s, tidak bisa menerima House baru." % (master.job_no, master.state))

        house_vals = self.env["freight.air.job"]._prepare_house_vals_from_quotation(
            self.quotation_id, master=self.master_job_id
        )
        house = self.env["freight.air.job"].create(house_vals)

        all_variants = house.source_quotation_id | house.source_quotation_id.variant_ids
        all_variants.write({"air_job_id": house.id})

        return {
            "type": "ir.actions.act_window",
            "name": "Air Job",
            "res_model": "freight.air.job",
            "res_id": house.id,
            "view_mode": "form",
            "target": "current",
        }
