from odoo import fields, models


class FreightDeclaration(models.Model):
    _name = 'freight.declaration'
    _description = 'Freight Declaration'
    _rec_name = 'name'

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Declaration Code must be unique!')
    ]

    code = fields.Char(string='DeclarationCode', required=True, size=3)
    name = fields.Char(string='Description')
    permit_id = fields.Many2one('freight.permit', string='Permit Code')
    active = fields.Boolean(string='Active', default=True)
