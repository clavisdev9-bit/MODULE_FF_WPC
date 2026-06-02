from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    city_id = fields.Many2one(
        comodel_name='res.city',
        string='Kabupaten / Kota',
        domain="[('state_id', '=?', state_id)]",
        required=False)
    subdistrict_id = fields.Many2one(
        comodel_name='res.subdistrict',
        string='Kecamatan',
        domain="[('city_id', '=?', city_id)]",
        required=False)
    village_id = fields.Many2one(
        comodel_name='res.village',
        string='Desa',
        domain="[('subdistrict_id', '=?', subdistrict_id)]",
        required=False)

    @api.onchange('village_id')
    def onchange_village(self):
        self.zip = self.village_id.zip
