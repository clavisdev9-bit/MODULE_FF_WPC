from odoo import fields, models


class FreightPermit(models.Model):
    _name = 'freight.permit'
    _description = 'Freight Permit'
    _rec_name = 'name'

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Permit Code must be unique!')
    ]

    code = fields.Char(string='Permit Code', required=True, size=5)
    name = fields.Char(string='Permit Description')
    active = fields.Boolean(string='Active', default=True)
