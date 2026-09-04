from odoo import models, fields


class HandlingInformation(models.Model):
    _name = 'freight.air.handling.information'
    _description = 'Air Handling Information'
    _rec_name = 'name'

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Handling Information Code must be unique!')
    ]

    code = fields.Char(string='Code')
    name = fields.Char(string='Name / Instruction', required=True)
    title = fields.Char(string='Title')
    description = fields.Text(string='Description / Full Text')
    active = fields.Boolean(string='Active', default=True)