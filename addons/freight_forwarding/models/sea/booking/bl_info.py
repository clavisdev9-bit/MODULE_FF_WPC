from odoo import api, fields, models


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
        compute="_compute_shipper_address",
        store=False,
    )

    consignee_id = fields.Many2one(
        "res.partner",
        string="Consignee",
        domain="[('category_id.name', '=', 'Consignee')]",
    )
    consignee_address = fields.Char(
        string="Consignee Address",
        compute="_compute_consignee_address",
        store=False,
    )

    notify_party_id = fields.Many2one(
        "res.partner",
        string="Notify Party",
        domain="[('category_id.name', '=', 'Notify Party')]",
    )
    notify_party_address = fields.Char(
        string="Notify Party Address",
        compute="_compute_notify_party_address",
        store=False,
    )

    @api.depends("shipper_id")
    def _compute_shipper_address(self):
        for rec in self:
            if rec.shipper_id:
                parts = [
                    rec.shipper_id.street,
                    rec.shipper_id.street2,
                    rec.shipper_id.city,
                    rec.shipper_id.state_id.name,
                    rec.shipper_id.country_id.name,
                ]
                rec.shipper_address = ", ".join([p for p in parts if p])
            else:
                rec.shipper_address = False

    @api.depends("consignee_id")
    def _compute_consignee_address(self):
        for rec in self:
            if rec.consignee_id:
                parts = [
                    rec.consignee_id.street,
                    rec.consignee_id.street2,
                    rec.consignee_id.city,
                    rec.consignee_id.state_id.name,
                    rec.consignee_id.country_id.name,
                ]
                rec.consignee_address = ", ".join([p for p in parts if p])
            else:
                rec.consignee_address = False

    @api.depends("notify_party_id")
    def _compute_notify_party_address(self):
        for rec in self:
            if rec.notify_party_id:
                parts = [
                    rec.notify_party_id.street,
                    rec.notify_party_id.street2,
                    rec.notify_party_id.city,
                    rec.notify_party_id.state_id.name,
                    rec.notify_party_id.country_id.name,
                ]
                rec.notify_party_address = ", ".join([p for p in parts if p])
            else:
                rec.notify_party_address = False
