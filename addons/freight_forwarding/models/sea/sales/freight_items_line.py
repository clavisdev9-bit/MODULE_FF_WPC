from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SeaQuotationItemsLine(models.Model):
    _name = "freight.sea.quotation.items.line"
    _inherit = "freight.sea.items.line.mixin"
    _description = "Sea Freight Quotation Items Line"
    _rec_name = "quotation_cargo_info_id"

    quotation_cargo_info_id = fields.Many2one(
        "freight.sea.quotation.cargo.info",
        string="Quotation Cargo Info",
        ondelete="cascade",
        required=True,
    )
    booking_package_details_id = fields.Many2one(
        "freight.sea.booking.detail.cargo",
        string="Booking Package Details",
        ondelete="cascade",
    )

    @api.constrains("quotation_cargo_info_id", "booking_package_details_id")
    def _check_single_parent(self):
        for record in self:
            has_quotation_parent = bool(record.quotation_cargo_info_id)
            has_booking_parent = bool(record.booking_package_details_id)
            if has_quotation_parent == has_booking_parent:
                raise ValidationError(
                    "Each freight item line must belong to exactly one parent: quotation cargo info or booking detail cargo."
                )
from odoo import fields, models


class SeaQuotationItemsLine(models.Model):
    _name = "freight.sea.quotation.items.line"
    _inherit = "freight.sea.items.line.mixin"
    _description = "Sea Freight Quotation Items Line"
    _rec_name = "quotation_cargo_info_id"

    quotation_cargo_info_id = fields.Many2one(
        "freight.sea.quotation.cargo.info",
        string="Quotation Cargo Info",
        ondelete="cascade",
        required=True,
    )
