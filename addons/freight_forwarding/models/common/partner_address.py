from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    street3 = fields.Char(string='Street 3')
    street4 = fields.Char(string='Street 4')
