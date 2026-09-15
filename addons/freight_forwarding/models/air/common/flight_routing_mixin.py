from odoo import fields, models

class FreightAirFlightRoutingMixin(models.AbstractModel):
    _name = 'freight.air.flight.routing.mixin'
    _description = 'Air Freight Flight Routing Mixin'

    airport_dest_id = fields.Many2one('freight.airport', string='To')
    airline_id = fields.Many2one('res.partner', string='By (Carrier)', domain="[('category_id.freight_role_code', '=', 'airline')]")
    flight_no = fields.Char(string='Flight No.')
    flight_date = fields.Date(string='On (Date)')
