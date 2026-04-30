from odoo import fields, models

class FreightLocation(models.Model):
    _name = "freight.location"
    _description = "Freight Location"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Location Code must be unique!")
    ]

    code = fields.Char(string="Location Code")
    name = fields.Char(string="Location Name", required=True)
    country_id = fields.Many2one("res.country", string="Country")
    active = fields.Boolean(string='Active', default=True)