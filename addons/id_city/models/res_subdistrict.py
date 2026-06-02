from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResSubdistrict(models.Model):
    _name = "res.subdistrict"
    _description = "Kecamatan"

    name = fields.Char(string='Kecamatan', required=True)
    city_id = fields.Many2one(
        comodel_name='res.city',
        string='Kabupaten / Kota',
        ondelete='cascade',
        required=True)
    village_ids = fields.One2many(
        comodel_name='res.village',
        inverse_name='subdistrict_id',
        string='Desa / Kelurahan',
        readonly=True)
