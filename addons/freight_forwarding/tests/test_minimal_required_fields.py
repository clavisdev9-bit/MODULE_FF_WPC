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
        self.assertFalse(booking.vessel_id)
        self.assertFalse(booking.partner_id)

    def test_air_booking_minimal(self):
        """freight_type punya default='export' (bukan blocking) -- yang
        diverifikasi di sini adalah create() tidak pernah gagal walau
        partner_id/business field lain kosong."""
        booking = self.env["freight.air.booking"].create({})
        self.assertTrue(booking.exists())
        self.assertFalse(booking.partner_id)

    def test_sea_hbl_minimal(self):
        hbl = self.env["freight.sea.hbl"].create({})
        self.assertTrue(hbl.exists())
        self.assertFalse(hbl.freight_type)
        self.assertFalse(hbl.container_type)

    def test_air_hawb_minimal(self):
        """freight_type punya default='export' (bukan blocking) -- yang
        diverifikasi di sini adalah create() tidak pernah gagal walau
        partner_id/business field lain kosong."""
        hawb = self.env["freight.air.hawb"].create({})
        self.assertTrue(hawb.exists())
        self.assertFalse(hawb.partner_id)

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

        hbl_result = booking.action_convert_to_hbl()
        hbl = self.env["freight.sea.hbl"].browse(hbl_result["res_id"])
        self.assertTrue(hbl.exists())

    def test_sea_quotation_direct_import_to_jobsheet_minimal(self):
        """Import direct: Quotation (cukup Customer) -> Jobsheet langsung."""
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "sea",
            "freight_type": "import",
        })
        result = quotation.action_convert_to_jobsheet_direct()
        hbl = self.env["freight.sea.hbl"].browse(result["res_id"])
        self.assertTrue(hbl.exists())

    def test_air_quotation_direct_import_to_jobsheet_minimal(self):
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "import",
        })
        result = quotation.action_convert_to_jobsheet_direct()
        hawb = self.env["freight.air.hawb"].browse(result["res_id"])
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

        hawb_result = booking.action_create_hawb()
        hawb = self.env["freight.air.hawb"].browse(hawb_result["res_id"])
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
        hbl = self.env["freight.sea.hbl"].create({})
        self.assertTrue(hbl.job_no)
        self.assertTrue(hbl.job_no.startswith("JKT-JOB/"),
            msg="job_no HBL tanpa freight_type harus pakai sequence netral, bukan EXP/IMP")

    def test_air_hawb_job_no_uses_neutral_sequence_when_freight_type_empty(self):
        hawb = self.env["freight.air.hawb"].create({})
        self.assertTrue(hawb.job_no)
        self.assertTrue(hawb.job_no.startswith("JKT-AJOB/"),
            msg="job_no HAWB tanpa freight_type harus pakai sequence netral, bukan AE/AI")
