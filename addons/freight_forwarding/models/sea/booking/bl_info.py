from odoo import fields, models


class SeaBookingBlInfo(models.Model):
    _name = "freight.sea.booking.bl.info"
    _description = "Sea Booking B/L Info"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )

    shipper_id = fields.Many2one(
        "res.partner",
        string="Shipper",
        domain="[('category_id.name', '=', 'Shipper')]",
    )
    shipper_address = fields.Char(
        string="Shipper Address",
        related="shipper_id.contact_address",
        readonly=True,
        store=False,
    )

    consignee_id = fields.Many2one(
        "res.partner",
        string="Consignee",
        domain="[('category_id.name', '=', 'Consignee')]",
    )
    consignee_address = fields.Char(
        string="Consignee Address",
        related="consignee_id.contact_address",
        readonly=True,
        store=False,
    )

    notify_party_id = fields.Many2one(
        "res.partner",
        string="Notify Party",
        domain="[('category_id.name', '=', 'Notify Party')]",
    )
    notify_party_address = fields.Char(
        string="Notify Party Address",
        related="notify_party_id.contact_address",
        readonly=True,
        store=False,
    )
