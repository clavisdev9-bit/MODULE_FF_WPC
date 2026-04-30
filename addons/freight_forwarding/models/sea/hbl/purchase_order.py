from odoo import fields, models


class SeaHBLPurchaseOrder(models.Model):
    _name = "freight.sea.hbl.purchase.order"
    _description = "Sea Jobsheet Purchase Order"
    _inherit = "freight.sea.purchase.order.mixin"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet",
        ondelete="cascade",
        required=True,
    )