from odoo import fields, models


class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    freight_role_code = fields.Char(string='Freight Role Code')
    is_freight_role = fields.Boolean(string='Is Freight Role')
