from odoo import fields, models

class FreightPort(models.Model):
    _name = "freight.port"
    _description = "Freight Port"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Port Code must be unique!")
    ]

    code = fields.Char(string="Port Code")
    name = fields.Char(string="Port Name", required=True)
    country_id = fields.Many2one("res.country", string="Country")
    active = fields.Boolean(string='Active', default=True)