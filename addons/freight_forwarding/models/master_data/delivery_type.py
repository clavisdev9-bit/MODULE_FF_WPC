from odoo import fields, models


class DeliveryType(models.Model):
    _name = "freight.delivery.type"
    _description = "Freight Delivery Type"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Delivery Type Code must be unique!")
    ]

    code = fields.Char(string="Delivery Type Code", required=True)
    name = fields.Char(string="Delivery Type Name", required=True)
    active = fields.Boolean(string="Active", default=True)