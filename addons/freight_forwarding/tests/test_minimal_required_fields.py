"""Kebijakan sementara: selama struktur Booking/Jobsheet dan Master/House
belum final, field bisnis/operasional TIDAK BOLEH memblokir create/save pada
Freight Quotation (sale.order), Booking (Air/Sea), maupun Jobsheet (Air/Sea).

Satu-satunya field wajib pada Freight Quotation adalah Customer (partner_id,
native sale.order, tidak diubah). Field teknis/system-generated (job_no,
booking name, company_id) tetap wajib -- itu bukan business input.
"""
from odoo.exceptions import UserError

from .common import FreightTestBase


class TestMinimalRequiredFields(FreightTestBase):

    def test_sea_quotation_minimal_customer_only(self):
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "sea",
        })
        self.assertTrue(quotation.exists())

    def test_air_quotation_minimal_customer_only(self):
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "air",
        })
        self.assertTrue(quotation.exists())

    def test_sea_booking_minimal(self):
        """Booking Sea harus bisa dibuat tanpa satupun business field."""
        booking = self.env["freight.sea.booking"].create({})
        self.assertTrue(booking.exists())
        self.assertFalse(booking.freight_type)
        self.assertFalse(booking.feeder_vessel_id)
        self.assertFalse(booking.mother_vessel_id)
        self.assertFalse(booking.partner_id)

    def test_air_booking_minimal(self):
        """FF-73 follow-up: freight_type TIDAK lagi punya default='export' --
        create() tanpa direction harus tetap sukses (bukan blocking) DAN
        freight_type harus tetap kosong (tidak diam-diam diklasifikasikan)."""
        booking = self.env["freight.air.booking"].create({})
        self.assertTrue(booking.exists())
        self.assertFalse(booking.partner_id)
        self.assertFalse(booking.freight_type)

    def test_sea_hbl_minimal(self):
        hbl = self.env["freight.sea.job"].create({})
        self.assertTrue(hbl.exists())
        self.assertFalse(hbl.freight_type)
        self.assertFalse(hbl.ship_mode)

    def test_air_hawb_minimal(self):
        """FF-73 follow-up: freight_type TIDAK lagi punya default='export' --
        create() tanpa direction harus tetap sukses (bukan blocking) DAN
        freight_type harus tetap kosong (tidak diam-diam diklasifikasikan).
        Sebelum fix ini, freight_type diam-diam jadi 'export' walau job_no
        (lihat TestConvertDoesNotGuessEmptyBusinessFields di bawah) memakai
        sequence netral -- semantic inconsistency."""
        hawb = self.env["freight.air.job"].create({"shipment_type": "direct"})
        self.assertTrue(hawb.exists())
        self.assertFalse(hawb.partner_id)
        self.assertFalse(hawb.freight_type)

    def test_sea_quotation_to_booking_to_jobsheet_minimal(self):
        """Quotation (cukup Customer) -> Booking -> Jobsheet harus berjalan
        walau field operasional lain belum lengkap."""
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "sea",
            "freight_type": "export",
        })
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        self.assertTrue(booking.exists())
        self.assertFalse(booking.feeder_vessel_id,
            msg="Sea Booking dari Quotation Export harus tetap bisa dibuat tanpa Vessel")
        self.assertFalse(booking.mother_vessel_id)

        hbl_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        self.assertTrue(master.exists())
        self.assertEqual(master.record_level, "master",
            msg="Booking -> Create Job harus membuat Master Job (FF-75)")
        self.assertEqual(len(master.house_job_ids), 1,
            msg="Booking -> Create Job harus otomatis membuat 1 House Job (FF-75)")

    def test_sea_quotation_direct_import_to_jobsheet_minimal(self):
        """Import direct: Quotation (cukup Customer) -> Jobsheet langsung."""
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "sea",
            "freight_type": "import",
        })
        result = quotation.action_convert_to_jobsheet_direct()
        hbl = self.env["freight.sea.job"].browse(result["res_id"])
        self.assertTrue(hbl.exists())

    def test_air_quotation_direct_import_to_jobsheet_minimal(self):
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "import",
        })
        result = quotation.action_convert_to_jobsheet_direct()
        hawb = self.env["freight.air.job"].browse(result["res_id"])
        self.assertTrue(hawb.exists())

    def test_air_quotation_to_booking_to_jobsheet_minimal(self):
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
        })
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        self.assertTrue(booking.exists())

        hawb_result = booking.action_create_job()
        hawb = self.env["freight.air.job"].browse(hawb_result["res_id"])
        self.assertTrue(hawb.exists())


class TestConvertDoesNotGuessEmptyBusinessFields(FreightTestBase):
    """FF-73 hardening pass: field bisnis boleh kosong saat draft/save, tapi
    action Convert yang butuh tahu arah Import/Export atau Air/Sea harus
    menolak eksplisit (UserError) kalau field itu kosong -- TIDAK boleh
    diam-diam jatuh ke salah satu pilihan lewat pola if/else."""

    def test_convert_quotation_without_freight_type_is_rejected_explicitly(self):
        """freight_type kosong -> action_convert_quotation harus menolak,
        bukan diam-diam masuk cabang else (Export/Booking)."""
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "sea",
            # freight_type sengaja kosong
        })
        with self.assertRaises(UserError):
            quotation.action_convert_quotation()

    def test_convert_to_booking_direct_without_freight_business_type_is_rejected_explicitly(self):
        """freight_business_type kosong -> action_convert_to_booking_direct
        harus menolak, bukan diam-diam masuk cabang else (Sea)."""
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_type": "export",
            # freight_business_type sengaja kosong
        })
        with self.assertRaises(UserError):
            quotation.action_convert_to_booking_direct()

    def test_convert_to_jobsheet_direct_without_freight_business_type_is_rejected_explicitly(self):
        """Sama seperti di atas, untuk jalur direct-import ke Jobsheet."""
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_type": "import",
            # freight_business_type sengaja kosong
        })
        with self.assertRaises(UserError):
            quotation.action_convert_to_jobsheet_direct()

    def test_sea_hbl_job_no_uses_neutral_sequence_when_freight_type_empty(self):
        """job_no tetap tergenerate (technical identity field), tapi TIDAK
        boleh memakai sequence Export maupun Import kalau freight_type
        belum ditentukan."""
        hbl = self.env["freight.sea.job"].create({})
        self.assertTrue(hbl.job_no)
        self.assertTrue(hbl.job_no.startswith("JKT-JOB/"),
            msg="job_no HBL tanpa freight_type harus pakai sequence netral, bukan EXP/IMP")

    def test_air_hawb_job_no_uses_neutral_sequence_when_freight_type_empty(self):
        hawb = self.env["freight.air.job"].create({"shipment_type": "direct"})
        self.assertTrue(hawb.job_no)
        self.assertTrue(hawb.job_no.startswith("JKT-AJOB/"),
            msg="job_no HAWB tanpa freight_type harus pakai sequence netral, bukan AE/AI")

    def test_air_booking_create_empty_diagnostic(self):
        """FF-73 diagnostic (item 5): sebelum fix, freight.air.booking punya
        default='export' pada freight_type -- create({}) diam-diam
        terklasifikasi Export walau user tidak pernah memilih direction.
        Setelah fix: freight_type harus tetap False (bukan 'export')."""
        booking = self.env["freight.air.booking"].create({})
        self.assertFalse(
            booking.freight_type,
            msg="freight.air.booking.create({}) TIDAK boleh diam-diam "
                "terklasifikasi 'export' -- business field kosong harus tetap kosong",
        )

    def test_air_hawb_create_empty_diagnostic_freight_type_and_job_no_consistent(self):
        """FF-73 diagnostic (item 5): kombinasi freight_type final DAN job_no
        prefix HAWB dari create({}) harus konsisten satu sama lain.

        Sebelum fix: default='export' pada field freight_type diterapkan
        ORM SETELAH FreightAirHawb.create() override membaca vals (vals
        kosong -> job_no pakai sequence netral JKT-AJOB/), sehingga hasil
        akhirnya freight_type='export' TAPI job_no berprefix netral --
        semantic inconsistency yang dilaporkan lewat assertion di bawah."""
        hawb = self.env["freight.air.job"].create({"shipment_type": "direct"})

        self.assertFalse(
            hawb.freight_type,
            msg="freight.air.job.create({}) TIDAK boleh diam-diam "
                "terklasifikasi 'export' -- business field kosong harus tetap kosong",
        )
        self.assertTrue(hawb.job_no.startswith("JKT-AJOB/"))
        # Konsistensi eksplisit: kalau freight_type falsy, job_no TIDAK boleh
        # memakai prefix Export (JKT-AE/) maupun Import (JKT-AI/).
        if not hawb.freight_type:
            self.assertFalse(hawb.job_no.startswith("JKT-AE/"))
            self.assertFalse(hawb.job_no.startswith("JKT-AI/"))
