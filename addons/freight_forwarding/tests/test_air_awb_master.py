"""FF-76 Air: AWB Master registry, assignment/availability, and
Booking/Master/House/Direct AWB identity normalization."""
from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from .common import FreightTestBase


class AirAwbTestBase(FreightTestBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.airport_dep = cls.env["freight.airport"].create({
            "code": "CGK", "name": "Soekarno-Hatta", "country_id": cls.env.ref("base.id").id,
        })
        cls.airport_dest = cls.env["freight.airport"].create({
            "code": "SIN", "name": "Changi", "country_id": cls.env.ref("base.sg").id,
        })
        cls.shipper = cls.env["res.partner"].create({"name": "Air Shipper Test"})

    def _create_awb(self, awb_no, **kwargs):
        vals = {"awb_no": awb_no}
        vals.update(kwargs)
        return self.env["freight.awb.master"].create(vals)

    def _create_air_booking(self, **kwargs):
        vals = {
            "freight_type": "export",
            "shipper_id": self.shipper.id,
            "destination_id": self.airport_dest.id,
            "pcs": 10,
            "gross_weight": 100.0,
        }
        vals.update(kwargs)
        return self.env["freight.air.booking"].create(vals)

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)


class TestAwbMasterModel(AirAwbTestBase):
    def test_awb_no_unique(self):
        """1. AWB Master awb_no unique."""
        self._create_awb("11122233344")
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(IntegrityError):
                self.env.cr.savepoint()
                self._create_awb("11122233344")

    def test_awb_type_separate_from_execution_shipment_type(self):
        """2. AWB Type adalah Air/Sea, terpisah dari Execution Shipment Type."""
        awb = self._create_awb("22233344455")
        self.assertEqual(awb.awb_type, "air", msg="Default AWB Type harus Air")
        self.assertIn(awb.awb_type, ("air", "sea"))
        self.assertFalse(awb.execution_shipment_type,
            msg="Execution Shipment Type kosong sebelum pernah di-assign")
        awb.awb_type = "sea"
        self.assertEqual(awb.awb_type, "sea")
        self.assertNotIn("master", [awb.awb_type])


class TestAwbBookingAssignment(AirAwbTestBase):
    def test_booking_assign_existing_awb_marks_executed_without_autofill(self):
        """3. UAT revision: Booking assign existing available AWB -> hanya
        menandai is_executed (historical usage internal); Execution Info
        TIDAK auto-fill dari Booking sama sekali (diisi manual oleh user)."""
        awb = self._create_awb("00112345678")
        booking = self._create_air_booking(awb_master_id=awb.id)

        self.assertTrue(awb.is_executed)
        self.assertEqual(awb.executed_booking_id, booking)
        self.assertFalse(awb.execution_shipment_type,
            msg="Execution Info tidak boleh auto-fill dari Booking")
        self.assertFalse(awb.execution_shipper_id)
        self.assertFalse(awb.execution_destination_id)
        self.assertEqual(awb.execution_pcs, 0)
        self.assertEqual(awb.execution_gross_weight, 0.0)
        self.assertFalse(awb.execute_by_id)
        self.assertFalse(awb.execute_date)

    def test_execution_info_is_manual_and_editable(self):
        """UAT revision: Execution Info bisa ditulis manual oleh user, kapan
        saja, dan tidak ter-overwrite oleh AWB assignment berikutnya."""
        awb = self._create_awb("00122345678")
        booking = self._create_air_booking(awb_master_id=awb.id)
        self.assertFalse(awb.execution_shipment_type)

        awb.write({
            "execution_shipment_type": "master",
            "execution_shipper_id": self.shipper.id,
            "execution_destination_id": self.airport_dest.id,
            "execution_pcs": 5,
            "execution_gross_weight": 50.0,
            "execute_by_id": self.env.uid,
            "execute_date": fields.Datetime.now(),
        })
        self.assertEqual(awb.execution_shipment_type, "master")
        self.assertEqual(awb.execution_pcs, 5)

        # Assignment lanjutan (mis. Master hasil Create Job) TIDAK boleh
        # menimpa ulang Execution Info yang sudah ditulis manual.
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        self.assertEqual(master.awb_master_id, awb)
        self.assertEqual(awb.execution_pcs, 5,
            msg="Execution Info manual tidak boleh ter-overwrite oleh AWB assignment")

    def test_booking_register_new_awb_defaults_air(self):
        """4. Booking register AWB baru -> default AWB Type Air."""
        awb = self.env["freight.awb.master"].create({"awb_no": "00199999999"})
        booking = self._create_air_booking(awb_master_id=awb.id)
        self.assertEqual(booking.awb_master_id.awb_type, "air")

    def test_awb_used_by_booking_b1_rejected_for_booking_b2(self):
        """5. AWB dipakai Booking B1 tidak dapat dipakai Booking B2.

        DB-level unique constraint (awb_master_id_uniq) menolak duplikasi
        antar 2 Booking lebih dulu (sebelum Python constrain sempat jalan)
        -- exception-nya IntegrityError, bukan ValidationError."""
        awb = self._create_awb("00212345678")
        self._create_air_booking(awb_master_id=awb.id)
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self.env.cr.savepoint()
                self._create_air_booking(awb_master_id=awb.id)

    def test_booking_create_job_master_uses_exact_same_awb_legal(self):
        """6. Booking B1 -> A1 -> Create Job: Master M1 pakai exact A1 sama,
        legal, dan snapshot A1 TIDAK di-overwrite lagi."""
        awb = self._create_awb("00312345678")
        booking = self._create_air_booking(awb_master_id=awb.id)
        original_execute_date = awb.execute_date

        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])

        self.assertEqual(master.shipment_type, "master")
        self.assertEqual(master.awb_master_id, awb,
            msg="Master harus memakai AWB Master yang EXACT sama dengan Booking")
        self.assertEqual(awb.execute_date, original_execute_date,
            msg="Snapshot AWB tidak boleh ditimpa ulang saat Master dibuat")
        self.assertEqual(awb.executed_booking_id, booking)

    def test_first_house_does_not_inherit_booking_awb(self):
        """7. First House hasil Booking tidak inherit A1."""
        awb = self._create_awb("00412345678")
        quotation = self._create_air_quotation()
        booking = self._create_air_booking(awb_master_id=awb.id, source_quotation_id=quotation.id)

        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        house = master.house_job_ids

        self.assertTrue(house, msg="House pertama harus otomatis dibuat dari source_quotation_id")
        self.assertFalse(house.awb_master_id,
            msg="House pertama tidak boleh otomatis mewarisi AWB dari Booking/Master")

    def test_booking_job_no_derived_from_master(self):
        """16. Booking.job_no kosong sebelum Master, derived setelahnya."""
        booking = self._create_air_booking()
        self.assertFalse(booking.job_no)

        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        self.assertEqual(booking.job_no, master.job_no)


class TestAwbMasterManualAndHouse(AirAwbTestBase):
    def test_manual_master_can_assign_existing_available_awb(self):
        """8. Manual Master dapat assign existing AVAILABLE AWB."""
        awb = self._create_awb("00512345678")
        master = self.env["freight.air.job"].create({
            "shipment_type": "master",
            "freight_type": "export",
            "awb_master_id": awb.id,
        })
        self.assertEqual(master.awb_master_id, awb)
        self.assertTrue(awb.is_executed)
        self.assertFalse(awb.execution_shipment_type,
            msg="Execution Info tidak boleh auto-fill dari Job")

    def test_house_can_assign_existing_available_awb(self):
        """9. House dapat assign existing AVAILABLE AWB."""
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        awb = self._create_awb("00612345678")
        house = self.env["freight.air.job"].create({
            "shipment_type": "house",
            "master_job_id": master.id,
            "freight_type": "export",
            "awb_master_id": awb.id,
        })
        self.assertEqual(house.awb_master_id, awb)
        self.assertTrue(awb.is_executed)
        self.assertFalse(awb.execution_shipment_type,
            msg="Execution Info tidak boleh auto-fill dari Job")

    def test_house_can_register_new_awb(self):
        """10. House dapat register AWB baru."""
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        awb = self.env["freight.awb.master"].create({"awb_no": "00699999999"})
        house = self.env["freight.air.job"].create({
            "shipment_type": "house",
            "master_job_id": master.id,
            "freight_type": "export",
            "awb_master_id": awb.id,
        })
        self.assertEqual(house.awb_master_id.awb_no, "00699999999")

    def test_house_h1_awb_cannot_be_used_by_house_h2(self):
        """11. House H1 AWB tidak dapat dipakai House H2.

        DB-level unique constraint (awb_master_id_uniq) menolak duplikasi
        antar 2 Job lebih dulu -- exception-nya IntegrityError."""
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        awb = self._create_awb("00712345678")
        self.env["freight.air.job"].create({
            "shipment_type": "house", "master_job_id": master.id,
            "freight_type": "export", "awb_master_id": awb.id,
        })
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self.env.cr.savepoint()
                self.env["freight.air.job"].create({
                    "shipment_type": "house", "master_job_id": master.id,
                    "freight_type": "export", "awb_master_id": awb.id,
                })

    def test_house_independent_awb_and_master_awb_helper_and_smawb(self):
        """12. House own awb != parent Master awb; master_awb_master_id
        membaca parent; smawb_no tetap tersedia."""
        master_awb = self._create_awb("00812345678")
        master = self.env["freight.air.job"].create({
            "shipment_type": "master", "freight_type": "export", "awb_master_id": master_awb.id,
        })
        house_awb = self._create_awb("00912345678")
        house = self.env["freight.air.job"].create({
            "shipment_type": "house", "master_job_id": master.id,
            "freight_type": "export", "awb_master_id": house_awb.id,
            "smawb_no": "SMAWB-001",
        })
        self.assertNotEqual(house.awb_master_id, master.awb_master_id)
        self.assertEqual(house.master_awb_master_id, master_awb)
        self.assertEqual(house.smawb_no, "SMAWB-001")


class TestAwbMasterDirect(AirAwbTestBase):
    def test_direct_can_assign_existing_available_awb(self):
        """13. Direct dapat assign existing AVAILABLE AWB."""
        awb = self._create_awb("01012345678")
        direct = self.env["freight.air.job"].create({
            "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb.id,
        })
        self.assertEqual(direct.awb_master_id, awb)
        self.assertTrue(awb.is_executed)
        self.assertFalse(awb.execution_shipment_type,
            msg="Execution Info tidak boleh auto-fill dari Job")

    def test_direct_cannot_reuse_awb_from_other_chain(self):
        """14. Direct tidak boleh reuse AWB yang sudah dipakai Master/House/Booking lain."""
        awb = self._create_awb("01112345678")
        self._create_air_booking(awb_master_id=awb.id)
        with self.assertRaises(ValidationError):
            self.env["freight.air.job"].create({
                "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb.id,
            })

        awb2 = self._create_awb("01212345678")
        master = self.env["freight.air.job"].create({
            "shipment_type": "master", "freight_type": "export", "awb_master_id": awb2.id,
        })
        # Master dan Direct sama-sama freight.air.job -- DB-level unique
        # constraint (awb_master_id_uniq) sudah menolak duplikasi ini lebih
        # dulu (IntegrityError), sebelum Python constrain sempat jalan.
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                self.env.cr.savepoint()
                self.env["freight.air.job"].create({
                    "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb2.id,
                })


class TestAwbSearchHelpers(AirAwbTestBase):
    def test_house_resolves_parent_mawb_and_parent_booking(self):
        """17. Search/helper House bisa resolve parent MAWB dan parent Booking."""
        awb = self._create_awb("01312345678")
        quotation = self._create_air_quotation()
        booking = self._create_air_booking(awb_master_id=awb.id, source_quotation_id=quotation.id)
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        house = master.house_job_ids

        self.assertEqual(house.master_awb_master_id, awb)
        self.assertEqual(house.effective_booking_id, booking)
        self.assertEqual(master.effective_booking_id, booking)

        found = self.env["freight.air.job"].search([("master_awb_master_id", "=", awb.id)])
        self.assertIn(house, found)
        found_by_booking = self.env["freight.air.job"].search([("effective_booking_id", "=", booking.id)])
        self.assertIn(house, found_by_booking)


class TestAwbReviewFindings(AirAwbTestBase):
    """Independent-review follow-up FF-76 Air: available-only candidate
    domain semantics, Air/Sea type invariant, controlled name_create."""

    def test_used_awb_excluded_from_available_domain_but_self_included(self):
        """1. Used AWB (chain lain) tidak termasuk candidate domain
        is_available=True; tapi domain gaya-view yang mengizinkan current
        value sendiri tetap meloloskan record itu untuk pemilik chain-nya."""
        awb = self._create_awb("02012345678")
        booking = self._create_air_booking(awb_master_id=awb.id)

        plain_available = self.env["freight.awb.master"].search([("is_available", "=", True)])
        self.assertNotIn(awb, plain_available,
            msg="AWB yang sudah used tidak boleh muncul di domain is_available=True")

        view_style_domain = ["|", ("is_available", "=", True), ("id", "=", booking.awb_master_id.id)]
        self_included = self.env["freight.awb.master"].search(view_style_domain)
        self.assertIn(awb, self_included,
            msg="Domain gaya-view (is_available OR current value) harus tetap meloloskan AWB milik record sendiri")

    def test_sea_type_awb_rejected_on_air_booking(self):
        """2. Sea-type AWB ditolak jika assign ke Air Booking."""
        sea_awb = self._create_awb("02112345678", awb_type="sea")
        with self.assertRaises(ValidationError):
            self._create_air_booking(awb_master_id=sea_awb.id)

    def test_sea_type_awb_rejected_on_air_job(self):
        """3. Sea-type AWB ditolak jika assign ke Air Job."""
        sea_awb = self._create_awb("02212345678", awb_type="sea")
        with self.assertRaises(ValidationError):
            self.env["freight.air.job"].create({
                "shipment_type": "direct", "freight_type": "export", "awb_master_id": sea_awb.id,
            })

    def test_executed_air_awb_cannot_become_sea(self):
        """4. Executed Air AWB tidak boleh diubah awb_type menjadi Sea."""
        awb = self._create_awb("02312345678")
        self.env["freight.air.job"].create({
            "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb.id,
        })
        self.assertTrue(awb.is_executed)
        with self.assertRaises(ValidationError):
            awb.write({"awb_type": "sea"})

    def test_name_create_existing_available_reuses_no_duplicate(self):
        """5. name_create existing+available -> reuse, tidak membuat duplicate."""
        existing = self._create_awb("02412345678")
        before_count = self.env["freight.awb.master"].search_count([("awb_no", "=", "02412345678")])
        self.assertEqual(before_count, 1)

        result_id, _ = self.env["freight.awb.master"].name_create("02412345678")
        self.assertEqual(result_id, existing.id)
        after_count = self.env["freight.awb.master"].search_count([("awb_no", "=", "02412345678")])
        self.assertEqual(after_count, 1, msg="name_create tidak boleh membuat duplicate untuk AWB yang sudah ada dan available")

    def test_name_create_existing_used_raises_clear_error(self):
        """6. name_create existing+used -> ValidationError jelas."""
        awb = self._create_awb("02512345678")
        self._create_air_booking(awb_master_id=awb.id)
        with self.assertRaises(ValidationError):
            self.env["freight.awb.master"].name_create("02512345678")

    def test_name_create_missing_creates_new_air_awb_from_context(self):
        """7. name_create tidak ada -> create baru, awb_type Air dari context."""
        result_id, _ = self.env["freight.awb.master"].with_context(
            default_awb_type="air"
        ).name_create("02612345678")
        new_awb = self.env["freight.awb.master"].browse(result_id)
        self.assertEqual(new_awb.awb_no, "02612345678")
        self.assertEqual(new_awb.awb_type, "air")

    def test_historical_used_awb_stays_blocked_after_owner_deleted(self):
        """Edge case follow-up: is_executed adalah source of truth historical
        usage -- BUKAN executed_job_id/executed_booking_id atau
        booking_ids/air_job_ids (yang bisa kosong kalau owner-nya dihapus).
        AWB yang pernah dieksekusi TETAP tidak boleh diubah Air -> Sea
        meski Job/Booking pemiliknya sudah dihapus."""
        awb = self._create_awb("03012345678")
        direct = self.env["freight.air.job"].create({
            "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb.id,
        })
        self.assertTrue(awb.is_executed)

        direct.unlink()
        awb.invalidate_recordset()
        self.assertTrue(awb.is_executed,
            msg="is_executed harus tetap True setelah owner Job dihapus")
        self.assertFalse(awb.executed_job_id,
            msg="executed_job_id boleh jadi null (ondelete set null) setelah owner dihapus")
        self.assertFalse(awb.air_job_ids,
            msg="reverse relation air_job_ids ikut kosong setelah owner dihapus")

        with self.assertRaises(ValidationError):
            awb.write({"awb_type": "sea"})

    def test_unused_air_awb_can_still_become_sea(self):
        """Existing behavior yang harus tetap lulus: AWB Air yang belum
        pernah dipakai sama sekali tetap boleh diubah ke Sea."""
        awb = self._create_awb("03112345678")
        self.assertFalse(awb.is_executed)
        awb.write({"awb_type": "sea"})
        self.assertEqual(awb.awb_type, "sea")


class TestAwbChainLockFinalHardening(AirAwbTestBase):
    """Final hardening FF-76 Air: proteksi delete AWB Master yang sudah
    used/terikat, dan lock identity Booking->Master AWB chain."""

    def test_unused_awb_master_can_unlink(self):
        """1. Unused AWB Master boleh dihapus."""
        awb = self._create_awb("04012345678")
        awb.unlink()
        self.assertFalse(awb.exists())

    def test_executed_awb_master_cannot_unlink(self):
        """2. Executed AWB Master tidak boleh dihapus."""
        awb = self._create_awb("04112345678")
        self.env["freight.air.job"].create({
            "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb.id,
        })
        self.assertTrue(awb.is_executed)
        with self.assertRaises(ValidationError):
            awb.unlink()

    def test_historical_used_awb_cannot_unlink_after_owner_deleted(self):
        """3. AWB historical-used tetap tidak bisa dihapus setelah owner
        relation-nya hilang (is_executed tetap True -- one-time usage rule
        tidak boleh ter-bypass lewat unlink lalu create ulang nomor sama)."""
        awb = self._create_awb("04212345678")
        direct = self.env["freight.air.job"].create({
            "shipment_type": "direct", "freight_type": "export", "awb_master_id": awb.id,
        })
        direct.unlink()
        awb.invalidate_recordset()
        self.assertTrue(awb.is_executed)
        self.assertFalse(awb.air_job_ids)
        with self.assertRaises(ValidationError):
            awb.unlink()

    def test_booking_awb_editable_before_master_exists(self):
        """4. Booking.awb_master_id tetap editable sebelum Master ada."""
        awb1 = self._create_awb("04312345678")
        awb2 = self._create_awb("04412345678")
        booking = self._create_air_booking(awb_master_id=awb1.id)
        self.assertEqual(booking.air_job_count, 0)
        booking.write({"awb_master_id": awb2.id})
        self.assertEqual(booking.awb_master_id, awb2)

    def test_booking_awb_cannot_change_after_master_exists(self):
        """5. Booking.awb_master_id tidak boleh berubah setelah Master ada."""
        awb1 = self._create_awb("04512345678")
        awb2 = self._create_awb("04612345678")
        booking = self._create_air_booking(awb_master_id=awb1.id)
        booking.action_create_job()
        self.assertTrue(booking.air_job_ids)
        with self.assertRaises(ValidationError):
            booking.write({"awb_master_id": awb2.id})

    def test_booking_awb_same_value_write_is_noop_allowed(self):
        """6. Write awb_master_id ke value yang SAMA tetap boleh (no-op) meski Master sudah ada."""
        awb1 = self._create_awb("04712345678")
        booking = self._create_air_booking(awb_master_id=awb1.id)
        booking.action_create_job()
        booking.write({"awb_master_id": awb1.id})
        self.assertEqual(booking.awb_master_id, awb1)

    def test_booking_created_master_awb_cannot_change(self):
        """7. Master.awb_master_id (hasil Booking) tidak boleh diedit independen."""
        awb1 = self._create_awb("04812345678")
        awb2 = self._create_awb("04912345678")
        booking = self._create_air_booking(awb_master_id=awb1.id)
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        with self.assertRaises(ValidationError):
            master.write({"awb_master_id": awb2.id})

    def test_booking_created_master_invariant_requires_same_awb(self):
        """8. Invariant: Master dengan booking_id harus awb_master_id ==
        booking_id.awb_master_id -- ditangkap constrain kalau di-bypass
        lewat write booking_id ke Booking lain yang AWB-nya berbeda."""
        awb1 = self._create_awb("05012345678")
        awb2 = self._create_awb("05112345678")
        booking1 = self._create_air_booking(awb_master_id=awb1.id)
        result = booking1.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])

        other_booking = self._create_air_booking(awb_master_id=awb2.id)
        with self.assertRaises(ValidationError):
            master.write({"booking_id": other_booking.id})

    def test_booking_create_job_same_awb_flow_still_passes(self):
        """9. Flow existing Booking -> Create Job dengan AWB yang sama tetap legal."""
        awb = self._create_awb("05212345678")
        booking = self._create_air_booking(awb_master_id=awb.id)
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        self.assertEqual(master.awb_master_id, awb)
        self.assertEqual(master.booking_id, booking)
        house = master.house_job_ids
        self.assertFalse(house.awb_master_id if house else False,
            msg="House pertama tetap AWB kosong")

    def test_manual_master_without_booking_outside_chain_lock(self):
        """10. Manual Master (tanpa booking_id) tidak terkena lock chain
        Booking -- awb_master_id-nya tetap bisa diedit selama masih legal
        (AWB baru yang available)."""
        awb1 = self._create_awb("05312345678")
        awb2 = self._create_awb("05412345678")
        master = self.env["freight.air.job"].create({
            "shipment_type": "master", "freight_type": "export", "awb_master_id": awb1.id,
        })
        self.assertFalse(master.booking_id)
        master.write({"awb_master_id": awb2.id})
        self.assertEqual(master.awb_master_id, awb2)


class TestAwbLateAssignment(AirAwbTestBase):
    """UAT revision FF-76: Booking AWB optional -- Create Job harus tetap
    berhasil tanpa AWB, dan AWB boleh di-assign belakangan lewat Master
    tanpa memaksa user menghapus Job."""

    def test_booking_without_awb_create_job_succeeds_master_empty(self):
        """Booking tanpa AWB -> Create Job sukses, Master juga kosong."""
        booking = self._create_air_booking()
        self.assertFalse(booking.awb_master_id)

        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        self.assertEqual(master.shipment_type, "master")
        self.assertFalse(master.awb_master_id)
        self.assertFalse(booking.awb_master_id)

    def test_late_assign_awb_from_master_propagates_to_booking(self):
        """Late assignment: assign AWB lewat Master -> Booking ikut
        mereferensikan AWB yang sama (satu source of truth per chain)."""
        booking = self._create_air_booking()
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])

        awb = self._create_awb("06012345678")
        master.write({"awb_master_id": awb.id})

        self.assertEqual(master.awb_master_id, awb)
        self.assertEqual(booking.awb_master_id, awb,
            msg="Booking harus ikut mereferensikan AWB yang sama setelah late assignment dari Master")
        self.assertTrue(awb.is_executed)

    def test_after_late_assignment_booking_and_master_cannot_diverge(self):
        """Setelah AWB terpasang lewat late assignment, Booking dan Master
        tidak boleh diedit independen menjadi AWB berbeda."""
        booking = self._create_air_booking()
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        awb = self._create_awb("06112345678")
        master.write({"awb_master_id": awb.id})

        other_awb = self._create_awb("06212345678")
        with self.assertRaises(ValidationError):
            master.write({"awb_master_id": other_awb.id})
        with self.assertRaises(ValidationError):
            booking.write({"awb_master_id": other_awb.id})

    def test_late_assignment_does_not_touch_execution_info(self):
        """AWB assignment (termasuk late assignment) tidak boleh mengisi
        atau menimpa Execution Info -- itu tetap murni manual."""
        booking = self._create_air_booking()
        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        awb = self._create_awb("06312345678")
        master.write({"awb_master_id": awb.id})

        self.assertFalse(awb.execution_shipment_type)
        self.assertFalse(awb.execution_shipper_id)
        self.assertFalse(awb.execute_by_id)
        self.assertFalse(awb.execute_date)
