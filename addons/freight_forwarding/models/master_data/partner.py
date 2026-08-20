from odoo import api, fields, models

class Partner(models.Model):
    _inherit = 'res.partner'
    
    city_id = fields.Many2one(
        'res.city',
        string='City',
        domain="[('country_id', '=?', country_id), ('state_id', '=?', state_id)]"
    )

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
            self.city = self.city_id.name
            if self.city_id.state_id:
                self.state_id = self.city_id.state_id
            if self.city_id.country_id:
                self.country_id = self.city_id.country_id
            if self.city_id.zipcode:
                self.zip = self.city_id.zipcode

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if hasattr(super(), '_onchange_state_id'):
            super()._onchange_state_id()
        if self.state_id and self.city_id and self.city_id.state_id and self.city_id.state_id != self.state_id:
            self.city_id = False

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if hasattr(super(), '_onchange_country_id'):
            super()._onchange_country_id()
        if self.country_id and self.city_id and self.city_id.country_id and self.city_id.country_id != self.country_id:
            self.city_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('city_id') and not vals.get('city'):
                city = self.env['res.city'].browse(vals['city_id'])
                if city:
                    vals['city'] = city.name
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('city_id') and not vals.get('city'):
            city = self.env['res.city'].browse(vals['city_id'])
            if city:
                vals['city'] = city.name
        return super().write(vals)