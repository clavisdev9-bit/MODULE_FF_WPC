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
    quotation_id = fields.Many2one(
        "freight.sea.quotation",
        string="Quotation No.",
        related="booking_id.quotation_id",
        store=True,
        required=False,
        readonly=True,
    )
    freight_items_line = fields.One2many(
        "freight.sea.booking.items.line",
        "booking_cargo_info_id",
        string="Freight Items Line",
    )