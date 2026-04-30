from odoo import fields, models


class SeaBookingShipmentInfo(models.Model):
    _name = "freight.sea.booking.shipment.info"
    _description = "Sea Booking Shipment Info"
    _inherit = "freight.sea.shipment.info.mixin"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )