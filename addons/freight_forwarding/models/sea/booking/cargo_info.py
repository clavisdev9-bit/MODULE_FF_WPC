from odoo import fields, models


class SeaBookingCargoInfo(models.Model):
    _name = "freight.sea.booking.cargo.info"
    _inherit = "freight.sea.cargo.info.mixin"
    _description = "Sea Booking Cargo Info"
    _rec_name = "booking_id"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )