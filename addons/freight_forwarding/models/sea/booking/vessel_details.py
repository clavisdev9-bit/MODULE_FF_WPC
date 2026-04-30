from odoo import fields, models


class SeaBookingVesselDetails(models.Model):
    _name = "freight.sea.booking.vessel.details"
    _description = "Sea Booking Vessel Details"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )

    # Booking & Agent Information
    principle_agent_id = fields.Many2one(
        "res.partner",
        string="Principal/Agent",
        domain="[('category_id.name', '=', 'Principal/Agent')]",
    )
    shipping_agent_id = fields.Many2one(
        "res.partner",
        string="Shipping Agent",
        domain="[('category_id.name', '=', 'Shipping Agent')]",
    )
    scn_code = fields.Char(string="SCN Code")

    # Stuffing Warehouse & SMK
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse Name")
    warehouse_address = fields.Char(
        related="warehouse_id.partner_id.contact_address",
        readonly=True,
        string="Warehouse Address",
    )
    smk_code1 = fields.Char(string="SMK Code 1")
    smk_code2 = fields.Char(string="SMK Code 2")

    # Scheduling & Receipt Details
    close_date = fields.Datetime(string="Close Date & Time")
    cargo_receipt_date = fields.Datetime(string="Cargo Receipt Date & Time")
    stuffing_date = fields.Datetime(string="Stuffing Date & Time")
    contact_id = fields.Many2one("res.partner", string="Contact")

    # Yard & Depot Details
    yard_id = fields.Many2one(
        "res.partner",
        string="Yard",
        domain="[('category_id.name', '=', 'Yard')]",
    )
    yard_code = fields.Char(
        related="yard_id.ref",
        string="Yard Code",
        readonly=True,
    )
    yard_address = fields.Char(
        related="yard_id.contact_address",
        string="Yard Address",
        readonly=True,
    )
    depot_id = fields.Many2one(
        "res.partner",
        string="Depot",
        domain="[('category_id.name', '=', 'Depot')]",
    )
    depot_code = fields.Char(
        related="depot_id.ref",
        string="Depot Code",
        readonly=True,
    )
    depot_address = fields.Char(
        related="depot_id.contact_address",
        string="Depot Address",
        readonly=True,
    )
    depot_instruction = fields.Many2one(
        "freight.instruction",
        string="Depot Instruction",
        domain="[('instruction_type', '=', 'depot')]",
    )

    general_instruction = fields.Many2one(
        "freight.instruction",
        string="General Instruction",
        domain="[('instruction_type', '=', 'general')]",
    )
