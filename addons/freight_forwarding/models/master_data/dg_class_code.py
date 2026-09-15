from odoo import fields, models


class FreightDgClassCode(models.Model):
    _name = 'freight.dg.class.code'
    _description = 'Freight DG Class Code'
    _rec_name = 'name'

    code = fields.Char(string='DG ClassCode')
    name = fields.Char(string='Substance / Description')
    un_no = fields.Char(string='UN No.')
    imo_class = fields.Char(string='IMO Class')
    group_name = fields.Char(string='Group Name')
    active = fields.Boolean(string='Active', default=True)
