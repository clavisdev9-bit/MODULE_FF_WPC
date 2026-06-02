from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResVillage(models.Model):
    _name = "res.village"
    _description = "Desa / Kelurahan"

    name = fields.Char(string='Desa / Kelurahan', required=True)
    subdistrict_id = fields.Many2one(
        comodel_name='res.subdistrict',
        string='Kecamatan',
        ondelete='cascade',
        required=True)
    zip = fields.Char(
        string='Kode POS',
        required=False)
