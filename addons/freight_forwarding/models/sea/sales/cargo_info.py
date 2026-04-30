from odoo import fields, models


class SeaQuotationCargoInfo(models.Model):
    _name = "freight.sea.quotation.cargo.info"
    _inherit = "freight.sea.cargo.info.mixin"
    _description = "Sea Quotation Cargo Info"
    _rec_name = "quotation_id"

    quotation_id = fields.Many2one(
        "freight.sea.quotation",
        string="Quotation No.",
        required=True,
        ondelete="cascade",
    )
    
    freight_items_line = fields.One2many(
        "freight.sea.quotation.items.line",
        "quotation_cargo_info_id",
        string="Freight Items Line",
    )