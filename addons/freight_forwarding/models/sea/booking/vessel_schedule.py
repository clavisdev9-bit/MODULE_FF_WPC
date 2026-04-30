from odoo import fields, models


class SeaBookingVesselSchedule(models.Model):
    _name = "freight.sea.booking.vessel.schedule"
    _description = "Sea Booking Vessel Schedule"

    shipment_info_id = fields.Many2one(
        "freight.sea.booking.shipment.info",
        string="Shipment Info",
        ondelete="cascade",
        required=True,
    )
    vessel_id = fields.Many2one("freight.vessel", string="Vessel")
    name = fields.Char(string="Schedule Reference")
    voyage_no = fields.Char(string="Voyage No.")
    arrival = fields.Datetime(string="Arrival")
    berthing = fields.Datetime(string="Berthing")
    departure = fields.Datetime(string="Departure")
    closing = fields.Datetime(string="Closing")
    terminal_id = fields.Many2one("freight.location", string="Terminal")
    status = fields.Char(string="Status")
    open_stack = fields.Datetime(string="Open Stack")
