from odoo import api, fields, models

class Partner(models.Model):
    _inherit = 'res.partner'
    
    city_id = fields.Many2one(
        'res.city',
        string='City',
        domain="[('country_id', '=?', country_id), ('state_id', '=?', state_id)]"
    )
    city = fields.Char(related='city_id.name', string='City', store=True, readonly=False)

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id:
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