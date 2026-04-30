from odoo import fields, models


class SeaShipmentInfoMixin(models.AbstractModel):
    _name = "freight.sea.shipment.info.mixin"
    _description = "Sea Shipment Info Mixin"

    # Shipment Details
    shipment_type_id = fields.Many2one("freight.delivery.type", string="Shipment Type")
    place_of_receipt_id = fields.Many2one("res.country.state", string="Place of Receipt")
    place_of_delivery_id = fields.Many2one("res.country.state", string="Place of Delivery")
    port_of_loading_id = fields.Many2one("freight.port", string="Port of Loading")
    port_of_discharge_id = fields.Many2one("freight.port", string="Port of Discharge")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    terminal_id = fields.Many2one("freight.location", string="Terminal")

    feeder_vessel_id = fields.Many2one("freight.vessel", string="Feeder Vessel")
    feeder_voyage_no = fields.Char(
        string="Feeder Voyage No.",
        related="feeder_vessel_id.voyage_no",
        readonly=True,
    )
    mother_vessel_id = fields.Many2one("freight.vessel", string="Mother Vessel")
    mother_voyage_no = fields.Char(
        string="Mother Voyage No.",
        related="mother_vessel_id.voyage_no",
        readonly=True,
    )
    shipping_line_id = fields.Many2one("freight.shipping.line", string="Shipping Line")
    shipping_line_ref_no = fields.Char(
        string="Shipping Line Ref No",
        related="shipping_line_id.shipping_line_ref_no",
        readonly=True,
        store=False,
    )
    coloader_id = fields.Many2one("res.partner", string="Coloader")
    coloader_ref_no = fields.Char(string="Coloader Ref No")
    stuffing_location_id = fields.Many2one("stock.warehouse", string="Stuffing Location")
    commodity_id = fields.Many2one("freight.commodity", string="Commodity")

    # Agent & Terms
    forward_agent_id = fields.Many2one(
        "res.partner",
        string="Forward Agent",
        domain="[('category_id.name', '=', 'Forward Agent')]",
    )
    letter_of_credit = fields.Char(string="Letter of Credit")
    freight_terms = fields.Selection(
        selection=[
            ("prepaid", "Prepaid"),
            ("collect", "Collect"),
        ],
        string="Freight Terms",
    )
    other_charges_terms = fields.Selection(
        selection=[
            ("prepaid", "Prepaid"),
            ("collect", "Collect"),
        ],
        string="Other Charges Terms",
    )
    ship_mode = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
        ],
        string="Ship Mode",
    )
    service_level = fields.Char(string="Service Level")

    # Vessel Schedule
    vessel_schedule_id = fields.Many2one(
        "freight.sea.booking.vessel.schedule",
        string="Vessel Schedule",
    )
    eta_jkt = fields.Date(string="ETA on JKT")
    etd_eta = fields.Datetime(string="ETD/ETA")
    via_etd = fields.Date(string="Via ETD")
    via_eta = fields.Date(string="Via ETA")

    # Footer Remark
    booking_remark_id = fields.Many2one(
        "freight.footer.remark", string="Booking Remark"
    )
    warehouse_remark = fields.Char(
        related="booking_remark_id.warehouse_remark",
        readonly=True,
        string="Warehouse Remark",
    )