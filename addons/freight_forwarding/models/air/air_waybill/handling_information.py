from odoo import models, fields


class HandlingInformation(models.Model):
    _name = 'freight.air.handling.information'
    _description = 'Air Handling Information'
    _rec_name = 'title'

    title = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')