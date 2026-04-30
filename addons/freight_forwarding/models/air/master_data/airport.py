from odoo import models, fields

class Airport(models.Model):
    _name = 'freight.airport'
    _description = 'Freight Airport'
    _rec_name = 'name'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Airport Code must be unique!')
    ]

    code = fields.Char(string='Airport Code', required = True)
    name = fields.Char(string='Airport Name', required = True)
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True
    )
    active = fields.Boolean(string='Active', default=True)