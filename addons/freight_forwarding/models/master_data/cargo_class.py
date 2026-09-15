from odoo import fields, models


class FreightCargoClass(models.Model):
    _name = 'freight.cargo.class'
    _description = 'Freight Cargo Class'
    _rec_name = 'name'

    code = fields.Char(string='Cargo Class Code')
    name = fields.Char(string='Cargo Class Description')
    active = fields.Boolean(string='Active', default=True)
