"""FF-76 Air: AWB Master registry, assignment/availability, and
Booking/Master/House/Direct AWB identity normalization."""
from psycopg2 import IntegrityError

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
    def test_booking_assign_existing_awb_snapshots_execution_info(self):
        """3. Booking assign existing available AWB -> snapshot Master info."""
        awb = self._create_awb("00112345678")
        booking = self._create_air_booking(awb_master_id=awb.id)

        self.assertTrue(awb.is_executed)
        self.assertEqual(awb.execution_shipment_type, "master")
        self.assertEqual(awb.execution_shipper_id, self.shipper)
        self.assertEqual(awb.execution_destination_id, self.airport_dest)
        self.assertEqual(awb.execution_pcs, 10)
        self.assertEqual(awb.execution_gross_weight, 100.0)
        self.assertEqual(awb.execute_by_id, self.env.user)
        self.assertTrue(awb.execute_date)
        self.assertEqual(awb.executed_booking_id, booking)

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
        self.assertEqual(awb.execution_shipment_type, "master")

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
        self.assertEqual(awb.execution_shipment_type, "house")

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
        self.assertEqual(awb.execution_shipment_type, "direct")

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


class TestAwbAirlinePrefixLookup(AirAwbTestBase):
    def test_master_awb_prefix_resolves_airline_code_with_leading_zero(self):
        """18. Master/Direct AWB '001...' resolve airline_code '001' tanpa
        menghilangkan leading zero."""
        airline = self.env["res.partner"].create({"name": "Test Airline", "airline_code": "001"})
        awb = self._create_awb("00123456789")
        self.env["freight.air.job"].create({
            "shipment_type": "master", "freight_type": "export", "awb_master_id": awb.id,
        })
        self.assertEqual(awb.airline_id, airline)

    def test_house_awb_does_not_do_airline_prefix_lookup(self):
        """19. House AWB tidak melakukan airline prefix lookup."""
        self.env["res.partner"].create({"name": "Test Airline 2", "airline_code": "002"})
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        house_awb = self._create_awb("00223456789")
        self.env["freight.air.job"].create({
            "shipment_type": "house", "master_job_id": master.id,
            "freight_type": "export", "awb_master_id": house_awb.id,
        })
        self.assertFalse(house_awb.airline_id,
            msg="House AWB tidak boleh resolve Airline dari prefix")
