from odoo import api, fields, models


class FreightPortDestination(models.Model):
    _name = 'freight.port.destination'
    _description = 'Freight Port Destination'

    port_id = fields.Many2one(
        'freight.port', required=True, ondelete='cascade',
    )
    destination_city_id = fields.Many2one('res.city', string='Destination City')
    destination_country_id = fields.Many2one(
        'res.country',
        string='Country',
        compute='_compute_destination_country_id',
        store=True,
        readonly=True,
    )
    no_of_day = fields.Integer(string='No. Of Day')

    @api.depends('destination_city_id')
    def _compute_destination_country_id(self):
        for rec in self:
            rec.destination_country_id = rec.destination_city_id.country_id or False
