from odoo import models, fields


class HandlingInformation(models.Model):
    _name = 'freight.air.handling.information'
    _description = 'Air Handling Information'
    _rec_names_search = ['code', 'name', 'description']
    _rec_name = 'description'

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Handling Information Code must be unique!')
    ]

    code = fields.Char(string='Code')
    name = fields.Char(string='Name / Instruction', required=True)
    title = fields.Char(string='Title')
    description = fields.Text(string='Description / Full Text')
    active = fields.Boolean(string='Active', default=True)

    def _compute_display_name(self):
        for rec in self:
            if rec.code:
                rec.display_name = f"[{rec.code}] {rec.name}"
            else:
                rec.display_name = rec.name or rec.description or ''