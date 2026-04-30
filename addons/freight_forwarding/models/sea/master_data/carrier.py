from odoo import fields, models

class FreightCarrier(models.Model):
    _name = "freight.carrier"
    _description = "Freight Carrier"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Carrier Code must be unique!")
    ]

    code = fields.Char(string="Carrier Code")
    name = fields.Char(string="Carrier Name", required=True)
    scac_code = fields.Char(string="SCAC Code")
    active = fields.Boolean(string='Active', default=True)