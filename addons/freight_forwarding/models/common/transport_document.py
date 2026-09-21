from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightTransportDocument(models.Model):
    """FF-76: canonical shared transport document registry (Air + Sea).
    Booking dan Job (Air, untuk saat ini) mereferensikan record ini lewat
    Many2one canonical `document_id` -- bukan lagi raw Char (awb_no/mawb_no/
    hawb_no/direct_awb_no).

    Genericization note (FF-76): model ini sebelumnya bernama
    `freight.awb.master` (Air-only naming) dan hidup di
    `models/air/awb/awb_master.py`. Business decision: registry ini memang
    shared concept lintas Air/Sea -- bukan model Air, bukan semata-mata AWB
    -- jadi source file-nya dipindahkan ke `models/common/` (bukan lagi di
    bawah namespace `models/air/`) dan model/terminology internal-nya
    di-generic-kan. Sea integration (sea_booking_ids/sea_job_ids, action/
    menu Sea dengan B/L terminology, dsb) SENGAJA belum dibuat di tahap ini
    -- hanya rename/generalization + relokasi file, bukan integrasi Sea.

    UI tetap terpisah per transport mode dan TIDAK di-generic-kan: Air
    (views/air/awb/awb_master.xml) tetap pakai terminology AWB ("AWB
    Master", "AWB No.", "AWB Type"); Sea nanti (belum dibuat) akan pakai
    terminology B/L di bawah views/sea/. Tidak ada satu menu/action
    gabungan Air+Sea.

    Physical SQL table dipertahankan sebagai `freight_awb_master` (lihat
    `_table` di bawah) supaya rename ini tidak memicu schema churn yang
    tidak perlu; migration ir.model/ir.model.fields/kolom bookkeeping ada
    di migrations/18.0.1.12/pre-migrate.py.

    Transport Document Code (nomor 3-digit prefix airline sebagai entity
    terpisah) SENGAJA belum diimplementasikan di tahap ini -- exact
    relationship-nya belum terbukti (lihat instruksi FF-76 tahap Air).

    UAT revision: SysFreight AWB Master form tidak menampilkan field
    Airline sama sekali -- field `airline_id` + prefix lookup adalah
    inference implementasi yang tidak terbukti dari evidence, sudah dihapus.
    """

    _name = "freight.transport.document"
    _table = "freight_awb_master"
    _description = "Transport Document Registry"
    _rec_name = "document_no"
    _order = "id desc"

    _sql_constraints = [
        ("document_no_uniq", "unique(document_no)", "Document No. harus unik."),
    ]

    document_no = fields.Char(string="Document No.", required=True, index=True, copy=False)
    transport_mode = fields.Selection(
        [("air", "Air"), ("sea", "Sea")],
        string="Transport Mode",
        required=True,
        default="air",
        help="Transport Mode = Air / Sea. BUKAN Master/House/Direct -- itu "
             "adalah Shipment Type (lihat shipment_type).",
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
    # Booking/Job manapun (lihat FreightTransportDocument._mark_used --
    # hanya menandai historical usage internal, tidak menyentuh field-field
    # ini).
    # ------------------------------------------------------------------
    shipment_type = fields.Selection(
        [("master", "Master"), ("house", "House"), ("direct", "Direct")],
        string="Shipment Type",
        copy=False,
    )
    shipper_id = fields.Many2one(
        "res.partner", string="Shipper", copy=False,
    )
    destination_id = fields.Many2one(
        "res.city", string="Destination", copy=False,
    )
    pcs = fields.Integer(string="Pcs", copy=False)
    gross_weight = fields.Float(string="Gross Weight", copy=False)
    execute_by_id = fields.Many2one(
        "res.users", string="Execute By", copy=False,
    )
    execute_date = fields.Datetime(string="Execute Date", copy=False)

    is_used = fields.Boolean(
        string="Used",
        default=False,
        copy=False,
        readonly=True,
        help="True setelah document ini pernah di-assign pertama kali. "
             "One-time semantic -- TIDAK boleh kembali False meski relation "
             "yang memakainya kemudian dilepas/diganti.",
    )
    # Historical usage pointer -- Air-only untuk saat ini (Sea integration
    # belum ada di tahap ini; JANGAN buat relation generic yang pura-pura
    # menunjuk dua model berbeda sebelum Sea benar-benar diintegrasikan).
    used_air_booking_id = fields.Many2one(
        "freight.air.booking",
        string="Used By Air Booking",
        readonly=True,
        copy=False,
        help="Air Booking yang memicu penandaan used pertama (kalau ada). "
             "Dipakai murni untuk validasi chain ownership -- bukan field bisnis.",
    )
    used_air_job_id = fields.Many2one(
        "freight.air.job",
        string="Used By Air Job",
        readonly=True,
        copy=False,
        help="Air Job yang memicu penandaan used pertama (kalau ada). "
             "Dipakai murni untuk validasi chain ownership -- bukan field bisnis.",
    )

    air_booking_ids = fields.One2many(
        "freight.air.booking", "document_id", string="Air Bookings", readonly=True,
    )
    air_job_ids = fields.One2many(
        "freight.air.job", "document_id", string="Air Jobs", readonly=True,
    )

    is_available = fields.Boolean(
        string="Available",
        compute="_compute_is_available",
        search="_search_is_available",
        help="Belum pernah di-assign/dipakai sama sekali. Bukan status "
             "operasional (USE/EXE/RSV dsb Sysfreight) -- murni indikator "
             "one-time-use registry.",
    )

    @api.depends("is_used")
    def _compute_is_available(self):
        for rec in self:
            rec.is_available = not rec.is_used

    def _search_is_available(self, operator, value):
        is_true = (operator == "=" and value) or (operator == "!=" and not value)
        return [("is_used", "!=" if is_true else "=", True)]

    @api.constrains("transport_mode")
    def _check_transport_mode_immutable_once_used(self):
        """Review follow-up FF-76: document yang sudah terikat (Booking/Job)
        atau pernah dipakai lewat chain Air TIDAK boleh diubah transport_mode
        dari Air ke Sea -- akan merusak invariant Air Booking/Job
        (document_id.transport_mode == 'air') yang sudah divalidasi terpisah.

        `is_used` adalah source of truth historical usage -- BUKAN
        `used_air_booking_id`/`used_air_job_id` (pointer itu bisa jadi null
        kalau owner Booking/Job-nya dihapus, ondelete set null) dan BUKAN
        cuma `air_booking_ids`/`air_job_ids` (reverse relation ikut kosong
        kalau owner dihapus). Document yang pernah is_used=True TETAP
        historical-used selamanya, terlepas relation-nya masih ada atau tidak."""
        for rec in self:
            if rec.transport_mode != "air" and (
                rec.is_used or rec.air_booking_ids or rec.air_job_ids
            ):
                raise ValidationError(
                    "Document %s sudah terikat/pernah digunakan oleh Air Booking "
                    "atau Air Job -- Transport Mode tidak boleh diubah dari Air "
                    "menjadi Sea." % rec.document_no
                )

    @api.model
    def name_create(self, name):
        """Review follow-up FF-76: exact Document No. quick-create yang
        terkontrol (dipakai widget Many2one Booking/House saat user
        mengetik nomor baru):
        - exact match sudah ada + available -> reuse record itu, jangan
          create duplicate.
        - exact match sudah ada tapi sudah used -> ValidationError jelas,
          jangan diam-diam gagal lewat SQL unique.
        - belum ada sama sekali -> create baru, transport_mode ikut context
          default_transport_mode (default Air untuk flow Air)."""
        existing = self.search([("document_no", "=", name)], limit=1)
        if existing:
            if not existing.is_available:
                raise ValidationError(
                    "Document %s sudah pernah digunakan / tidak available." % name
                )
            return existing.id, existing.display_name
        transport_mode = self.env.context.get("default_transport_mode") or "air"
        new_doc = self.create({"document_no": name, "transport_mode": transport_mode})
        return new_doc.id, new_doc.display_name

    def _mark_used(self, air_booking=None, air_job=None):
        """UAT revision FF-76: Execution Info sekarang diisi MANUAL oleh
        user (lihat komentar field di atas) -- TIDAK ada lagi auto-fill/
        snapshot dari Booking/Job. Method ini HANYA menandai internal
        one-time historical usage (`is_used` + pointer ownership untuk
        validasi chain), dipisahkan total dari Execution Info yang visible.

        Dipanggil setiap kali document_id di-set pada Booking/Job; no-op
        kalau document ini sudah pernah dipakai sebelumnya (one-time
        semantic -- owner pointer pertama yang menang, chain legality lain
        divalidasi lewat constrain masing-masing model konsumen)."""
        self.ensure_one()
        if self.is_used:
            return
        vals = {"is_used": True}
        if air_booking is not None:
            vals["used_air_booking_id"] = air_booking.id
        if air_job is not None:
            vals["used_air_job_id"] = air_job.id
        self.write(vals)

    def unlink(self):
        """Final hardening FF-76: document yang sudah pernah dipakai
        (is_used) atau masih terikat ke Booking/Job (air_booking_ids/
        air_job_ids) TIDAK boleh dihapus -- kalau boleh, nomor yang sama
        bisa dibuat ulang dan one-time usage rule (is_used) ter-bypass.
        Document yang benar-benar unused/unbound tetap boleh dihapus
        seperti biasa."""
        for rec in self:
            if rec.is_used or rec.air_booking_ids or rec.air_job_ids:
                raise ValidationError(
                    "Document %s sudah pernah digunakan/terikat ke Booking atau "
                    "Job -- tidak boleh dihapus." % rec.document_no
                )
        return super().unlink()
