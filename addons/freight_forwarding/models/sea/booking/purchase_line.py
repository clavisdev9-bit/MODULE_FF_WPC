from odoo import fields, models


class SeaBookingPurchaseOrder(models.Model):
    _name = "freight.sea.booking.purchase.order"
    _description = "Sea Booking Purchase Order"
    _inherit = "freight.sea.purchase.order.mixin"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )
