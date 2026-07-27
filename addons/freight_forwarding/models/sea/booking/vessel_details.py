from odoo import fields, models


class SeaBookingVesselDetails(models.Model):
    _name = "freight.sea.booking.vessel.details"
    _description = "Sea Booking Vessel Details"
    _inherit = "freight.sea.vessel.details.mixin"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )
    freight_type = fields.Selection(
        related="booking_id.freight_type",
        string="Type",
        store=True,
        readonly=True,
    )
