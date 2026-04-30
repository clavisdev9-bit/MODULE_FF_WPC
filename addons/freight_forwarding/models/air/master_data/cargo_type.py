from odoo import models, fields

class CargoType(models.Model):
    _name = 'freight.cargo.type'
    _description = 'Freight Cargo Type'
    _rec_name = 'name'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Cargo Type Code must be unique!')
    ]

    code = fields.Char(string='Cargo Type Code', required = True)
    name = fields.Char(string='Cargo Type Name', required = True)
    active = fields.Boolean(string='Active', default=True)
