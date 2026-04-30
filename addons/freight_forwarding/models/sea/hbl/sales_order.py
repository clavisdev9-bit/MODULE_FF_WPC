from odoo import fields, models


class SeaHBLSalesOrder(models.Model):
    _name = "freight.sea.hbl.sales.order"
    _description = "Sea Jobsheet Sales Order"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet",
        ondelete="cascade",
        required=True,
    )
    sales_order_id = fields.Many2one(
        "sale.order",
        string="Order Reference",
    )
    vendor = fields.Many2one(
        "res.partner",
        related="sales_order_id.partner_id",
        string="Vendor",
        store=True,
        readonly=True,
    )
    currency = fields.Many2one(
        "res.currency",
        related="sales_order_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )
    amount = fields.Monetary(
        related="sales_order_id.amount_total",
        currency_field="currency",
        string="Amount",
        store=True,
        readonly=True,
    )