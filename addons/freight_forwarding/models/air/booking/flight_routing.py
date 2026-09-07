from odoo import fields, models

class FreightAirBookingFlightRouting(models.Model):
    _name = 'freight.air.booking.flight.routing'
    _inherit = 'freight.air.flight.routing.mixin'
    _description = 'Air Booking Flight Routing'

    booking_id = fields.Many2one('freight.air.booking', string='Booking', ondelete='cascade', required=True)
