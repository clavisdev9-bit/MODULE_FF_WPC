from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightAwbMaster(models.Model):
    """FF-76: canonical AWB registry (Master AWB record). Booking dan Job
    (Air) mereferensikan record ini lewat Many2one canonical `awb_master_id`
    -- bukan lagi raw Char (awb_no/mawb_no/hawb_no/direct_awb_no).

    AWB Code (nomor 3-digit prefix airline sebagai entity terpisah) SENGAJA
    belum diimplementasikan di tahap ini -- exact relationship-nya belum
    terbukti (lihat instruksi FF-76 tahap Air).

    UAT revision: SysFreight AWB Master form tidak menampilkan field
    Airline sama sekali -- field `airline_id` + prefix lookup adalah
    inference implementasi yang tidak terbukti dari evidence, sudah dihapus.
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
    # Execution Info -- UAT revision: SysFreight mengisi field-field ini
    # SECARA MANUAL oleh user, bukan auto-fill/snapshot dari Booking/Job.
    # Semua field di bawah ini editable dan TIDAK live-sync ke perubahan
    # Booking/Job manapun (lihat FreightAwbMaster._mark_executed -- hanya
    # menandai historical usage internal, tidak menyentuh field-field ini).
    # ------------------------------------------------------------------
    execution_shipment_type = fields.Selection(
        [("master", "Master"), ("house", "House"), ("direct", "Direct")],
        string="Shipment Type",
        copy=False,
    )
    execution_shipper_id = fields.Many2one(
        "res.partner", string="Shipper", copy=False,
    )
    execution_destination_id = fields.Many2one(
        "freight.airport", string="Destination", copy=False,
    )
    execution_pcs = fields.Integer(string="Pcs", copy=False)
    execution_gross_weight = fields.Float(string="Gross Weight", copy=False)
    execute_by_id = fields.Many2one(
        "res.users", string="Execute By", copy=False,
    )
    execute_date = fields.Datetime(string="Execute Date", copy=False)

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

    @api.depends("is_executed")
    def _compute_is_available(self):
        for rec in self:
            rec.is_available = not rec.is_executed

    def _search_is_available(self, operator, value):
        is_true = (operator == "=" and value) or (operator == "!=" and not value)
        return [("is_executed", "!=" if is_true else "=", True)]

    @api.constrains("awb_type")
    def _check_awb_type_immutable_once_bound_to_air(self):
        """Review follow-up FF-76: AWB yang sudah terikat (Booking/Job) atau
        pernah di-execute lewat chain Air TIDAK boleh diubah awb_type-nya
        dari Air ke Sea -- akan merusak invariant Air Booking/Job
        (awb_master_id.awb_type == 'air') yang sudah divalidasi terpisah.

        `is_executed` adalah source of truth historical usage -- BUKAN
        `executed_booking_id`/`executed_job_id` (pointer itu bisa jadi null
        kalau owner Booking/Job-nya dihapus, ondelete set null) dan BUKAN
        cuma `booking_ids`/`air_job_ids` (reverse relation ikut kosong kalau
        owner dihapus). AWB yang pernah is_executed=True TETAP historical-used
        selamanya, terlepas relation-nya masih ada atau tidak."""
        for rec in self:
            if rec.awb_type != "air" and (
                rec.is_executed or rec.booking_ids or rec.air_job_ids
            ):
                raise ValidationError(
                    "AWB %s sudah terikat/pernah digunakan oleh Air Booking atau "
                    "Air Job -- AWB Type tidak boleh diubah dari Air menjadi Sea." % rec.awb_no
                )

    @api.model
    def name_create(self, name):
        """Review follow-up FF-76: exact AWB No. quick-create yang
        terkontrol (dipakai widget Many2one Booking/House saat user
        mengetik nomor baru):
        - exact match sudah ada + available -> reuse record itu, jangan
          create duplicate.
        - exact match sudah ada tapi sudah used -> ValidationError jelas,
          jangan diam-diam gagal lewat SQL unique.
        - belum ada sama sekali -> create baru, awb_type ikut context
          default_awb_type (default Air untuk flow Air)."""
        existing = self.search([("awb_no", "=", name)], limit=1)
        if existing:
            if not existing.is_available:
                raise ValidationError(
                    "AWB %s sudah pernah digunakan / tidak available." % name
                )
            return existing.id, existing.display_name
        awb_type = self.env.context.get("default_awb_type") or "air"
        new_awb = self.create({"awb_no": name, "awb_type": awb_type})
        return new_awb.id, new_awb.display_name

    def _mark_executed(self, booking=None, job=None):
        """UAT revision FF-76: Execution Info sekarang diisi MANUAL oleh
        user (lihat komentar field di atas) -- TIDAK ada lagi auto-fill/
        snapshot dari Booking/Job. Method ini HANYA menandai internal
        one-time historical usage (`is_executed` + pointer ownership untuk
        validasi chain), dipisahkan total dari Execution Info yang visible.

        Dipanggil setiap kali awb_master_id di-set pada Booking/Job;
        no-op kalau AWB ini sudah pernah di-execute sebelumnya (one-time
        semantic -- owner pointer pertama yang menang, chain legality lain
        divalidasi lewat _check_awb_master_chain masing-masing model)."""
        self.ensure_one()
        if self.is_executed:
            return
        vals = {"is_executed": True}
        if booking is not None:
            vals["executed_booking_id"] = booking.id
        if job is not None:
            vals["executed_job_id"] = job.id
        self.write(vals)

    def unlink(self):
        """Final hardening FF-76: AWB yang sudah pernah dipakai (is_executed)
        atau masih terikat ke Booking/Job (booking_ids/air_job_ids) TIDAK
        boleh dihapus -- kalau boleh, nomor yang sama bisa dibuat ulang dan
        one-time usage rule (is_executed) ter-bypass. AWB yang benar-benar
        unused/unbound tetap boleh dihapus seperti biasa."""
        for rec in self:
            if rec.is_executed or rec.booking_ids or rec.air_job_ids:
                raise ValidationError(
                    "AWB %s sudah pernah digunakan/terikat ke Booking atau Job -- "
                    "tidak boleh dihapus." % rec.awb_no
                )
        return super().unlink()
