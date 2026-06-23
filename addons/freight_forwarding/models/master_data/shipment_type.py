from odoo import fields, models


class ShipmentType(models.Model):
    _name = "freight.shipment.type"
    _description = "Freight Shipment Type"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Shipment Type Code must be unique!")
    ]

    code = fields.Char(string="Shipment Type Code", required=True)
    name = fields.Char(string="Shipment Type Name", required=True)
    active = fields.Boolean(string="Active", default=True)