from odoo import fields, models


class SeaHBLItemsLine(models.Model):
    _name = "freight.sea.hbl.items.line"
    _inherit = "freight.sea.items.line.mixin"
    _description = "Sea Freight Jobsheet Items Line"
    _rec_name = "hbl_cargo_info_id"

    hbl_cargo_info_id = fields.Many2one(
        "freight.sea.hbl.cargo.info",
        string="HBL Cargo Info",
        ondelete="cascade",
        required=True,
    )
