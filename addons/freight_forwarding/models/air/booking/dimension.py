from odoo import fields, models

class FreightAirBookingDimension(models.Model):
    _name = 'freight.air.booking.dimension'
    _inherit = 'freight.air.dimension.mixin'
    _description = 'Air Booking Dimension'

    booking_id = fields.Many2one('freight.air.booking', string='Booking', ondelete='cascade', required=True)
