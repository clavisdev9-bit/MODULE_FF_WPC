from odoo import api, fields, models
from odoo.exceptions import UserError


class SeaAddToMasterWizard(models.TransientModel):
    """FF-75: wizard 'Add to Master' -- Quotation Export tambahan (Q2, Q3, ...)
    digabungkan ke Master Sea existing tanpa membuat Booking baru. House baru
    dibuat dari Quotation aktif dan langsung ter-gabung (master_job_id) ke
    Master yang dipilih di sini."""

    _name = "freight.sea.add.to.master.wizard"
    _description = "Sea Add to Master Wizard"

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
        "freight.sea.job",
        string="Master Job",
        required=True,
        domain="[('record_level', '=', 'master'), ('freight_type', '=', freight_type),"
               " ('company_id', '=', company_id), ('state', 'not in', ['closed', 'cancelled']),"
               " '|', ('ship_mode', '!=', 'fcl'), ('house_job_ids', '=', False)]",
        help="Master harus Freight Type & Company yang sama dengan Quotation, "
             "berstatus aktif (bukan Closed/Cancelled). Sea FCL yang sudah "
             "punya 1 House tidak akan muncul di sini.",
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
        quotation = self.quotation_id
        if not quotation.is_freight_quotation:
            raise UserError("Quotation yang dipilih bukan Freight Quotation.")
        if quotation.freight_business_type != "sea":
            raise UserError("Add to Master Sea hanya berlaku untuk Quotation Sea.")
        if quotation.freight_type != "export":
            raise UserError("Add to Master hanya berlaku untuk Quotation Export.")

        master = self.master_job_id
        if master.record_level != "master":
            raise UserError("Job yang dipilih harus berupa Master Job.")
        if master.freight_type != self.quotation_id.freight_type:
            raise UserError("Master harus punya Type (Import/Export) yang sama dengan Quotation.")
        if master.company_id != self.quotation_id.company_id:
            raise UserError("Master harus berada di Company yang sama dengan Quotation.")
        if master.state in ("closed", "cancelled"):
            raise UserError("Master (%s) sudah %s, tidak bisa menerima House baru." % (master.job_no, master.state))
        if master.ship_mode == "fcl" and master.house_job_ids:
            raise UserError(
                "Sea FCL (%s) sudah memiliki 1 House Job." % master.job_no
            )

        house_vals = self.env["freight.sea.job"]._prepare_house_vals_from_quotation(
            self.quotation_id, master=self.master_job_id
        )
        house = self.env["freight.sea.job"].create(house_vals)

        all_variants = house.source_quotation_id | house.source_quotation_id.variant_ids
        all_variants.write({"sea_job_id": house.id})
        all_variants.write({"sea_job_ids": [(4, house.id)]})

        return {
            "type": "ir.actions.act_window",
            "name": "Sea Job",
            "res_model": "freight.sea.job",
            "res_id": house.id,
            "view_mode": "form",
            "target": "current",
        }
