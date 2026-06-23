from odoo import models, fields

class ContainerType(models.Model):
    _name = 'freight.container.type'
    _description = 'Freight Container/Box Type'
    _rec_name = 'code'

    _sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'Container Type Code must be unique!')
    ]

    code = fields.Char(string='Container Type Code', required=True)
    name = fields.Char(string='Description', required=True)

    size_code = fields.Char(string='Size Code')
    iso_size = fields.Char(string='ISO Size')

    no_of_teu = fields.Float(string='No of TEU')
    max_cubic_foot = fields.Float(string='Max Cubic Foot')
    max_volume_m3 = fields.Float(string='Max Volume m3')
    max_weight_kg = fields.Float(string='Max Weight kg')

    temperature_flag = fields.Boolean(string='Temperature Flag')
    active = fields.Boolean(string='Active', default=True)
