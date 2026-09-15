from odoo import fields, models


class Commodity(models.Model):
    _name = "freight.commodity"
    _description = "Freight Commodity"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Commodity Code must be unique!")
    ]

    code = fields.Char(string="Commodity Code", required=True, size=10)
    name = fields.Char(string="Commodity Name", required=True)
    hs_code = fields.Char(string="HS Code")
    dutiable = fields.Boolean(string="Dutiable")
    active = fields.Boolean(string="Active", default=True)