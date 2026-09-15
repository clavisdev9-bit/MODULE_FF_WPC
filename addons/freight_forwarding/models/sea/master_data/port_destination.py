from odoo import fields, models


class FreightPortDestination(models.Model):
    _name = 'freight.port.destination'
    _description = 'Freight Port Destination'

    port_id = fields.Many2one(
        'freight.port', required=True, ondelete='cascade',
    )
    destination_city_id = fields.Many2one('res.city', string='Destination City')
    no_of_day = fields.Integer(string='No. Of Day')
