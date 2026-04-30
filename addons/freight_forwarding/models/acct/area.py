from odoo import models, fields

class Area(models.Model):
    _name = 'freight.area'
    _description = 'Freight Area'
    _rec_name = 'name'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Area Code must be unique!')
    ]

    code = fields.Char(string='Area Code', required = True)
    name = fields.Char(string='Area Name', required = True)
    active = fields.Boolean(string='Active', default=True)