from odoo import fields, models


class FreightShippingLine(models.Model):
    _name = "freight.shipping.line"
    _description = "Freight Shipping Line"
    _rec_name = "name"

    _sql_constraints = [
        (
            "code_unique",
            "UNIQUE(code)",
            "Shipping Line Code must be unique!",
        ),
        (
            "identifier_unique",
            "UNIQUE(shipping_line_identifier)",
            "Shipping Line ID must be unique!",
        ),
    ]

    code = fields.Char(string="Shipping Line Code", required=True)
    name = fields.Char(string="Shipping Line Name", required=True)
    shipping_line_identifier = fields.Char(string="Shipping Line ID")
    shipping_line_ref_no = fields.Char(string="Shipping Line Ref No")
    active = fields.Boolean(string="Active", default=True)