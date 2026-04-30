from odoo import models, fields

class Pickup(models.Model):
    _name = 'freight.pickup'
    _description = 'Freight Pickup'
    _rec_name = 'name'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Pickup Code must be unique!')
    ]

    code = fields.Char(string='Pickup Code', required=True)
    name = fields.Char(string='Pickup Address', required=True)
    transportation_method = fields.Selection(
        selection=[
            ('air', 'Air'),
            ('ocean', 'Ocean'),
            ('domestic', 'Domestic Ground Transportation'),
        ],
        string='Transportation Method'
    )
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one(
        'res.country.state', 
        domain="[('country_id', '=', country_id)]",
        string='State')
    active = fields.Boolean(string='Active', default=True)
