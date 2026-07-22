from odoo import fields, models


class SeaHBLCargoInfo(models.Model):
    _name = "freight.sea.hbl.cargo.info"
    _inherit = "freight.sea.cargo.info.mixin"
    _description = "Sea Jobsheet Cargo Info"
    _rec_name = "hbl_id"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet",
        ondelete="cascade",
    )
    hbl_no = fields.Char(
        string="Jobsheet No.",
        related="hbl_id.hbl_no",
        store=True,
        readonly=True,
    )
    type = fields.Selection(
        related="hbl_id.freight_type",
        string="Type",
        store=True,
        readonly=True,
    )
    freight_type = fields.Selection(
        related="hbl_id.container_type",
        string="Container Type",
        store=True,
        readonly=True,
    )
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        related="hbl_id.booking_id",
        store=True,
        readonly=True,
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="hbl_id.customer_id",
        store=True,
        readonly=True,
    )
    freight_items_line = fields.One2many(
        "freight.sea.hbl.items.line",
        "hbl_cargo_info_id",
        string="Freight Items Line",
    )
