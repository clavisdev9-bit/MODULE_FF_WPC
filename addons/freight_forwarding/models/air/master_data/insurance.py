from odoo import models, fields

class Insurance(models.Model):
    _name = 'freight.insurance'
    _description = 'Freight Insurance'
    _rec_name = 'name'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Insurance Code must be unique!')
    ]

    code = fields.Char(string='Insurance Code', required=True)
    name = fields.Char(string='Insurance Name', required=True)
    active = fields.Boolean(string='Active', default=True)
