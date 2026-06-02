from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCity(models.Model):
    _name = "res.city"
    _description = "City"

    name = fields.Char(string='City', required=True)
    state_id = fields.Many2one(
        comodel_name='res.country.state',
        string='State',
        ondelete='cascade',
        domain=[],
        required=True)
    # subdistrict_ids = fields.One2many(
    #     comodel_name='res.subdistrict',
    #     inverse_name='city_id',
    #     string='Subdistrict',
    #     readonly=True)