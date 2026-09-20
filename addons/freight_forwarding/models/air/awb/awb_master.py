from odoo import api, fields, models


class FreightAwbMaster(models.Model):
    """FF-76: canonical AWB registry (Master AWB record). Booking dan Job
    (Air) mereferensikan record ini lewat Many2one canonical `awb_master_id`
    -- bukan lagi raw Char (awb_no/mawb_no/hawb_no/direct_awb_no).

    AWB Code (nomor 3-digit prefix airline sebagai entity terpisah) SENGAJA
    belum diimplementasikan di tahap ini -- exact relationship-nya belum
    terbukti (lihat instruksi FF-76 tahap Air). Airline hanya di-derive
    read-only dari 3 karakter pertama awb_no, bukan FK wajib.
    """

    _name = "freight.awb.master"
    _description = "AWB Master / Registry"
    _rec_name = "awb_no"
    _order = "id desc"

    _sql_constraints = [
        ("awb_no_uniq", "unique(awb_no)", "AWB No. harus unik."),
    ]

    awb_no = fields.Char(string="AWB No.", required=True, index=True, copy=False)
    awb_type = fields.Selection(
        [("air", "Air"), ("sea", "Sea")],
        string="AWB Type",
        required=True,
        default="air",
        help="AWB Type = Air / Sea. BUKAN Master/House/Direct -- itu adalah "
             "Execution Shipment Type (lihat execution_shipment_type).",
    )
    service_level = fields.Char(
        string="Service Level",
        help="Domain bisnis exact belum dikonfirmasi -- Char sederhana, "
             "tidak mengunci selection dari model lain sebagai source of truth.",
    )

    # ------------------------------------------------------------------
    # Execution Info -- SNAPSHOT, bukan related/live-sync ke Booking/Job.
    # Diisi sekali saat AWB pertama kali di-assign (lihat _snapshot_from_*).
    # ------------------------------------------------------------------
    execution_shipment_type = fields.Selection(
        [("master", "Master"), ("house", "House"), ("direct", "Direct")],
        string="Shipment Type",
        readonly=True,
        copy=False,
    )
    execution_shipper_id = fields.Many2one(
        "res.partner", string="Shipper", readonly=True, copy=False,
    )
    execution_destination_id = fields.Many2one(
        "freight.airport", string="Destination", readonly=True, copy=False,
    )
    execution_pcs = fields.Integer(string="Pcs", readonly=True, copy=False)
    execution_gross_weight = fields.Float(string="Gross Weight", readonly=True, copy=False)
    execute_by_id = fields.Many2one(
        "res.users", string="Execute By", readonly=True, copy=False,
    )
    execute_date = fields.Datetime(string="Execute Date", readonly=True, copy=False)

    is_executed = fields.Boolean(
        string="Executed",
        default=False,
        copy=False,
        readonly=True,
        help="True setelah AWB ini pernah di-assign/snapshot pertama kali. "
             "One-time semantic -- TIDAK boleh kembali False meski relation "
             "yang memakainya kemudian dilepas/diganti.",
    )
    executed_booking_id = fields.Many2one(
        "freight.air.booking",
        string="Executed By Booking",
        readonly=True,
        copy=False,
        help="Booking yang memicu snapshot pertama (kalau ada). Dipakai "
             "murni untuk validasi chain ownership -- bukan field bisnis.",
    )
    executed_job_id = fields.Many2one(
        "freight.air.job",
        string="Executed By Job",
        readonly=True,
        copy=False,
        help="Job yang memicu snapshot pertama (kalau ada). Dipakai murni "
             "untuk validasi chain ownership -- bukan field bisnis.",
    )

    booking_ids = fields.One2many(
        "freight.air.booking", "awb_master_id", string="Air Bookings", readonly=True,
    )
    air_job_ids = fields.One2many(
        "freight.air.job", "awb_master_id", string="Air Jobs", readonly=True,
    )

    is_available = fields.Boolean(
        string="Available",
        compute="_compute_is_available",
        search="_search_is_available",
        help="Belum pernah di-assign/dieksekusi sama sekali. Bukan status "
             "operasional (USE/EXE/RSV dsb Sysfreight) -- murni indikator "
             "one-time-use registry.",
    )

    airline_id = fields.Many2one(
        "res.partner",
        string="Airline",
        compute="_compute_airline_id",
        help="Derived read-only dari 3 karakter pertama AWB No. (exact "
             "match ke res.partner.airline_code), hanya untuk AWB Type Air "
             "dengan Execution Shipment Type Master/Direct. House tidak "
             "melakukan prefix lookup (House AWB bisa arbitrary/internal).",
    )

    @api.depends("is_executed")
    def _compute_is_available(self):
        for rec in self:
            rec.is_available = not rec.is_executed

    def _search_is_available(self, operator, value):
        is_true = (operator == "=" and value) or (operator == "!=" and not value)
        return [("is_executed", "!=" if is_true else "=", True)]

    @api.depends("awb_no", "awb_type", "execution_shipment_type")
    def _compute_airline_id(self):
        for rec in self:
            airline = False
            if (
                rec.awb_type == "air"
                and rec.execution_shipment_type in ("master", "direct")
                and rec.awb_no
                and len(rec.awb_no) >= 3
            ):
                prefix = rec.awb_no[:3]
                airline = self.env["res.partner"].search(
                    [("airline_code", "=", prefix)], limit=1
                )
            rec.airline_id = airline.id if airline else False

    def _snapshot_from_booking(self, booking):
        """FF-76: snapshot Execution Info dari Booking, HANYA sekali per AWB.
        Dipanggil setiap kali awb_master_id di-set pada Booking; no-op kalau
        AWB ini sudah pernah di-execute sebelumnya (mis. Master yang dibuat
        dari Booking memakai AWB yang sama -- snapshot A1 milik Booking
        TIDAK boleh ditimpa lagi)."""
        self.ensure_one()
        if self.is_executed:
            return
        self.write({
            "execution_shipment_type": "master",
            "execution_shipper_id": booking.shipper_id.id if booking.shipper_id else False,
            "execution_destination_id": booking.destination_id.id if booking.destination_id else False,
            "execution_pcs": booking.pcs,
            "execution_gross_weight": booking.gross_weight,
            "execute_by_id": self.env.uid,
            "execute_date": fields.Datetime.now(),
            "is_executed": True,
            "executed_booking_id": booking.id,
        })

    def _snapshot_from_job(self, job):
        """FF-76: snapshot Execution Info dari Job (Master/House/Direct),
        HANYA sekali per AWB. Lihat catatan idempotency di _snapshot_from_booking."""
        self.ensure_one()
        if self.is_executed:
            return
        self.write({
            "execution_shipment_type": job.shipment_type,
            "execution_shipper_id": job.shipper_id.id if job.shipper_id else False,
            "execution_destination_id": job.destination_id.id if job.destination_id else False,
            "execution_pcs": job.pcs,
            "execution_gross_weight": job.gross_weight,
            "execute_by_id": self.env.uid,
            "execute_date": fields.Datetime.now(),
            "is_executed": True,
            "executed_job_id": job.id,
        })
