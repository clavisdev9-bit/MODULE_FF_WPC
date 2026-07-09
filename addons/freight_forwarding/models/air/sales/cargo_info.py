from odoo import fields, models


class AirQuotationCargoInfo(models.Model):
    _name = "freight.air.quotation.cargo.info"
    _inherit = "freight.sea.cargo.info.mixin"
    _description = "Air Quotation Cargo Info"
    _rec_name = "quotation_id"

    quotation_id = fields.Many2one(
        "freight.air.quotation",
        string="Quotation No.",
        required=True,
        ondelete="cascade",
    )
