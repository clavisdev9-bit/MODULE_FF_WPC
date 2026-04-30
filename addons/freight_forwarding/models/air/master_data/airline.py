from odoo import models, fields

class Airline(models.Model):
    _name = 'freight.airline'
    _description = 'Freight Airline'
    _rec_name = 'name'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Airline Code must be unique!')
    ]

    code = fields.Char(string='Airline Code', required = True)
    name = fields.Char(string='Airline Name', required = True)
    awb_prefix = fields.Char(string='AWB Prefix')
    active = fields.Boolean(string='Active', default=True)