from odoo import api, models

class City(models.Model):
    _inherit = 'res.city'

    @api.depends('zipcode')
    def _compute_display_name(self):
        super()._compute_display_name()
        for city in self:
            city.display_name = city.name