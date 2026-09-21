from odoo import fields, models


class SeaBookingVesselSchedule(models.Model):
    _name = "freight.sea.booking.vessel.schedule"
    _description = "Sea Booking Vessel Schedule"

    _sql_constraints = [
        (
            "booking_or_hbl_required",
            "CHECK(booking_id IS NOT NULL OR job_id IS NOT NULL)",
            "Vessel Schedule harus terhubung ke Booking atau Jobsheet.",
        )
    ]

    # NOTE (FF-22): sebelumnya FK ke freight.sea.booking.shipment.info
    # (model perantara yang sudah dihapus). Model ini dipakai bersama oleh
    # Booking dan HBL lewat field vessel_schedule_id di
    # freight.sea.shipment.info.mixin, jadi FK diarahkan langsung ke
    # booking_id / job_id -- keduanya opsional (hanya salah satu yang
    # terisi tergantung record ini dibuat dari konteks Booking atau HBL).
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
    )
    job_id = fields.Many2one(
        "freight.sea.job",
        string="Jobsheet",
        ondelete="cascade",
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