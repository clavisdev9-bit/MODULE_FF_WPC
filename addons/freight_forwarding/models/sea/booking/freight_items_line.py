from odoo import fields, models


class SeaBookingItemsLine(models.Model):
    _name = "freight.sea.booking.items.line"
    _inherit = "freight.sea.items.line.mixin"
    _description = "Sea Freight Booking Items Line"
    _rec_name = "booking_cargo_info_id"

    booking_cargo_info_id = fields.Many2one(
        "freight.sea.booking.cargo.info",
        string="Booking Cargo Info",
        ondelete="cascade",
        required=True,
    )
