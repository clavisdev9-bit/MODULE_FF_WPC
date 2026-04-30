from odoo import fields, models


class SeaPurchaseOrderMixin(models.AbstractModel):
    _name = "freight.sea.purchase.order.mixin"
    _description = "Sea Purchase Order Mixin"

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Order Reference",
    )
    vendor = fields.Many2one(
        "res.partner",
        related="purchase_order_id.partner_id",
        string="Vendor",
        store=True,
        readonly=True,
    )
    currency = fields.Many2one(
        "res.currency",
        related="purchase_order_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )
    amount = fields.Monetary(
        related="purchase_order_id.amount_total",
        currency_field="currency",
        string="Amount",
        store=True,
        readonly=True,
    )