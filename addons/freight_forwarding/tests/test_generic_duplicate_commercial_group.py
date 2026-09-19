"""FF-73 follow-up: regression test untuk generic Duplicate (copy() tanpa
default apa pun -- BUKAN action_create_currency_variant()).

Sebelum fix ini, booking_ids/sea_job_ids/sea_job_id (Sea) dan
air_booking_ids/air_job_id (Air) di sale.order punya copy=True (default
Odoo untuk Many2one/Many2many). Generic Duplicate atas quotation yang sudah
punya Booking/Jobsheet ikut menyalin field-field itu ke record BARU yang
independen (original_quotation_id-nya tetap False, BUKAN currency variant),
lalu SeaQuotation.create()/AirQuotation.create() menuliskannya balik ke
Booking/Jobsheet.sale_order_ids -- constraint freight.commercial.group.mixin
lalu menolak WRITE itu karena duplicate bukan anggota commercial group root
manapun. Akibatnya generic Duplicate GAGAL (ValidationError) hanya karena
field compatibility mirror FF-73, padahal Duplicate semestinya independen.

Fix: field-field itu sekarang copy=False (lihat models/sea/sales/quotation.py
dan models/air/sales/quotation.py). Test ini memverifikasi symptom lama
sudah tidak terjadi, dan currency variant (jalur yang memang HARUS tetap
tersinkron) tidak ikut rusak."""
from .common import FreightTestBase


class TestSeaGenericDuplicateCommercialGroup(FreightTestBase):

    def test_duplicate_of_root_with_booking_and_jobsheet_is_independent(self):
        """A -> Booking -> Jobsheet, lalu Duplicate generic dari A."""
        quotation = self._create_quotation()  # A
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: action_create_job membuka Master; House pertama (yang
        # menyimpan sale_order_ids/source_quotation_id sendiri) otomatis
        # dibuat sebagai child-nya -- Master shell tidak menyimpan sale_order_ids.
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids

        self.assertIn(quotation, booking.sale_order_ids)
        self.assertIn(quotation, hbl.sale_order_ids)

        # Generic Duplicate -- HARUS tidak gagal karena constraint commercial
        # group FF-73 (regression yang di-fix).
        duplicate = quotation.copy()

        self.assertFalse(
            duplicate.original_quotation_id,
            msg="Duplicate generic bukan currency variant -- original_quotation_id harus False",
        )
        self.assertNotIn(
            duplicate, booking.sale_order_ids,
            msg="Duplicate generic TIDAK boleh otomatis masuk Booking.sale_order_ids milik A",
        )
        self.assertNotIn(
            duplicate, hbl.sale_order_ids,
            msg="Duplicate generic TIDAK boleh otomatis masuk Jobsheet.sale_order_ids milik A",
        )
        self.assertNotIn(
            booking, duplicate.booking_ids,
            msg="Duplicate generic TIDAK boleh mewarisi booking_ids mirror milik A",
        )
        self.assertNotIn(
            hbl, duplicate.sea_job_ids,
            msg="Duplicate generic TIDAK boleh mewarisi sea_job_ids mirror milik A",
        )
        self.assertNotIn(
            duplicate, booking._get_commercial_group(),
            msg="Duplicate generic TIDAK boleh dikenali sebagai anggota commercial group A",
        )

    def test_duplicate_of_direct_import_jobsheet_quotation_is_independent(self):
        """Jalur direct-import (sea_job_id, bukan lewat Booking)."""
        quotation = self._create_quotation(freight_type="import")  # A
        result = quotation.action_convert_to_jobsheet_direct()
        # FF-75: action membuka Master; House pertamanya yang menyimpan
        # sea_job_id/sale_order_ids terkait quotation.
        master = self.env["freight.sea.job"].browse(result["res_id"])
        hbl = master.house_job_ids

        self.assertEqual(quotation.sea_job_id, hbl)
        self.assertIn(quotation, hbl.sale_order_ids)

        duplicate = quotation.copy()

        self.assertFalse(duplicate.original_quotation_id)
        self.assertFalse(
            duplicate.sea_job_id,
            msg="Duplicate generic TIDAK boleh mewarisi sea_job_id milik A",
        )
        self.assertNotIn(
            duplicate, hbl.sale_order_ids,
            msg="Duplicate generic TIDAK boleh otomatis masuk Jobsheet.sale_order_ids milik A",
        )

    def test_currency_variant_still_syncs_to_existing_booking_and_jobsheet(self):
        """Kontras dengan Duplicate generic: Currency Variant HARUS tetap
        tersinkron ke Booking/Jobsheet existing (fix di atas tidak boleh
        merusak jalur ini)."""
        quotation = self._create_quotation()  # A
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: lihat komentar setara di test_duplicate_of_root_with_booking_and_jobsheet_is_independent.
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids

        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        self.assertEqual(variant.original_quotation_id, quotation)
        self.assertIn(variant, booking.sale_order_ids,
            msg="Currency variant HARUS otomatis masuk Booking.sale_order_ids (beda dengan Duplicate generic)")
        self.assertIn(variant, hbl.sale_order_ids,
            msg="Currency variant HARUS otomatis masuk Jobsheet.sale_order_ids (beda dengan Duplicate generic)")
        self.assertIn(booking, variant.booking_ids)
        self.assertIn(hbl, variant.sea_job_ids)


class TestAirGenericDuplicateCommercialGroup(FreightTestBase):

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_duplicate_of_root_with_booking_and_hawb_is_independent(self):
        quotation = self._create_air_quotation()  # A
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        hawb_result = booking.action_create_job()
        hawb = self.env["freight.air.job"].browse(hawb_result["res_id"])

        self.assertIn(quotation, booking.sale_order_ids)

        # Generic Duplicate -- HARUS tidak gagal karena constraint commercial
        # group FF-73.
        duplicate = quotation.copy()

        self.assertFalse(duplicate.original_quotation_id)
        self.assertNotIn(
            duplicate, booking.sale_order_ids,
            msg="Duplicate generic TIDAK boleh otomatis masuk Air Booking.sale_order_ids milik A",
        )
        self.assertFalse(
            duplicate.air_job_id,
            msg="Duplicate generic TIDAK boleh mewarisi air_job_id milik A",
        )
        self.assertNotIn(
            booking, duplicate.air_booking_ids,
            msg="Duplicate generic TIDAK boleh mewarisi air_booking_ids mirror milik A",
        )
        if hawb.sale_order_ids:
            self.assertNotIn(
                duplicate, hawb.sale_order_ids,
                msg="Duplicate generic TIDAK boleh otomatis masuk HAWB.sale_order_ids milik A",
            )

    def test_currency_variant_still_syncs_air_booking(self):
        quotation = self._create_air_quotation()  # A
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])

        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        self.assertEqual(variant.original_quotation_id, quotation)
        self.assertIn(variant, booking.sale_order_ids,
            msg="Currency variant Air HARUS otomatis masuk Air Booking.sale_order_ids")
