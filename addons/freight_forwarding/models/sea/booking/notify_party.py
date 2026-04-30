from odoo import fields, models


class SeaBookingNotifyParty(models.Model):
    _name = "freight.sea.booking.notify.party"
    _description = "Sea Booking Notify Party"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )
    notify_name_id = fields.Many2one(
        "res.partner",
        string="Notify Name",
        domain="[('category_id.name', '=', 'Notify Party')]",
    )
    notify_code = fields.Char(string="Notify Code")
    notify_address = fields.Text(string="Notify Address")
    also_notify_name_id = fields.Many2one(
        "res.partner",
        string="Also Notify Name",
        domain="[('category_id.name', '=', 'Notify Party')]",
    )
    also_notify_code = fields.Char(string="Also Notify Code")
    also_notify_address = fields.Text(string="Also Notify Address")
