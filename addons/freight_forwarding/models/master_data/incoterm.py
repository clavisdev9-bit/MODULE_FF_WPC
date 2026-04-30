from odoo import fields, models

class FreightIncoterm(models.Model):
    _name = "freight.incoterm"
    _description = "Freight Incoterm"
    _rec_name = "code"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Incoterm Code must be unique!")
    ]

    code = fields.Char(string="Incoterm Code")
    name = fields.Char(string="Incoterm Name", required=True)
    active = fields.Boolean(string='Active', default=True)