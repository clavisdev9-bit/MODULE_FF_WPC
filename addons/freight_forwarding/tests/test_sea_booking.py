"""Test untuk Sea Booking model."""
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger

from .common import FreightTestBase


class TestSeaBookingFields(FreightTestBase):
    """Verifikasi field constraints pada Sea Booking."""

    def test_freight_type_not_required(self):
        """Kebijakan sementara: freight_type (dan field bisnis Booking
        lainnya) TIDAK BOLEH memblokir create selama struktur Booking/
        Jobsheet belum final. Booking tanpa freight_type harus tetap
        berhasil dibuat."""
        booking = self.env["freight.sea.booking"].create({
            "partner_id": self.partner.id,
            # freight_type, ship_mode, feeder_vessel_id/mother_vessel_id,
            # delivery_type_id sengaja tidak diisi -- harus tetap berhasil.
        })
        self.assertTrue(booking.exists())
        self.assertFalse(booking.freight_type)
        self.assertFalse(booking.feeder_vessel_id)
        self.assertFalse(booking.mother_vessel_id)

    def test_freight_type_valid_values(self):
        """freight_type hanya menerima 'import' atau 'export' (lowercase)."""
        booking_export = self._create_booking(freight_type="export")
        booking_import = self._create_booking(freight_type="import")

        self.assertEqual(booking_export.freight_type, "export")
        self.assertEqual(booking_import.freight_type, "import")

    def test_unique_quotation_constraint(self):
        """Satu quotation tidak bisa dipakai di dua booking berbeda."""
        quotation = self._create_quotation()
        self._create_booking(quotation_id=quotation.id)

        with mute_logger("odoo.sql_db"):
            with self.assertRaises((IntegrityError, Exception),
                    msg="Quotation yang sama di booking kedua harus ditolak"):
                self.env.cr.savepoint()
                self._create_booking(quotation_id=quotation.id)


class TestSeaBookingConvertToHbl(FreightTestBase):
    """Verifikasi action_create_job — konversi booking ke HBL."""

    def test_convert_creates_hbl(self):
        """action_create_job membuat satu HBL baru."""
        booking = self._create_booking(freight_type="export")
        self.assertEqual(booking.sea_job_count, 0)

        booking.action_create_job()

        self.assertEqual(booking.sea_job_count, 1,
            msg="Harus ada tepat 1 HBL setelah convert")

    def test_convert_hbl_inherits_freight_type(self):
        """HBL yang dibuat mewarisi freight_type dari booking — tanpa konversi manual."""
        booking_export = self._create_booking(freight_type="export")
        booking_import = self._create_booking(freight_type="import")

        booking_export.action_create_job()
        booking_import.action_create_job()

        hbl_export = booking_export.sea_job_ids[0]
        hbl_import = booking_import.sea_job_ids[0]

        # Kunci: HBL pakai casing yang sama persis (lowercase) dengan booking
        self.assertEqual(hbl_export.freight_type, "export",
            msg="HBL harus inherit 'export' langsung dari booking")
        self.assertEqual(hbl_import.freight_type, "import",
            msg="HBL harus inherit 'import' langsung dari booking")

    def test_convert_idempotent(self):
        """Memanggil action_create_job dua kali tidak membuat HBL baru."""
        booking = self._create_booking()

        booking.action_create_job()
        booking.action_create_job()  # panggil lagi

        self.assertEqual(booking.sea_job_count, 1,
            msg="Harus tetap 1 HBL meski convert dipanggil dua kali")

    def test_convert_copies_cargo_info(self):
        """Cargo info di booking di-copy ke HBL saat convert."""
        booking = self._create_booking()
        self._create_booking_cargo_info(booking, quantity=5)
        self._create_booking_cargo_info(booking, quantity=3)

        booking.action_create_job()

        hbl = booking.sea_job_ids[0]
        self.assertEqual(len(hbl.cargo_info_ids), 2,
            msg="Semua cargo info dari booking harus ter-copy ke HBL")

    def test_convert_returns_action_to_hbl(self):
        """action_create_job mengembalikan action window ke HBL."""
        booking = self._create_booking()
        result = booking.action_create_job()

        self.assertEqual(result.get("res_model"), "freight.sea.job",
            msg="Action harus mengarah ke model freight.sea.job")
        self.assertEqual(result.get("view_mode"), "form")

    def test_convert_copies_bl_info(self):
        """Field-field B/L info (termasuk notify_same_as_consignee) di-copy ke HBL saat convert."""
        booking = self._create_booking(
            consignee_id=self.partner.id,
            notify_party_id=self.partner.id,
            notify_same_as_consignee=True,
        )
        booking.action_create_job()

        hbl = booking.sea_job_ids[0]
        self.assertEqual(hbl.consignee_id, self.partner)
        self.assertEqual(hbl.notify_party_id, self.partner)
        self.assertTrue(hbl.notify_same_as_consignee)

    def test_convert_copies_shipment_type(self):
        """shipment_type_id (Many2one freight.shipment.type) tersalin otomatis ke HBL saat convert (FF-52)."""
        shipment_type = self.env["freight.shipment.type"].create({
            "name": "FCL / FCL",
        })
        booking = self._create_booking(shipment_type_id=shipment_type.id)
        booking.action_create_job()

        hbl = booking.sea_job_ids[0]
        self.assertEqual(hbl.shipment_type_id, shipment_type,
            msg="shipment_type_id harus ter-copy dari Booking ke HBL")

    def test_convert_copies_customer_reference_and_depot(self):
        """customer_reference disalin ke customer_ref, dan depot (id, code, address) disalin ke HBL (FF-53)."""
        booking = self._create_booking(
            customer_reference="CUST-REF-12345",
            depot_id="DEPOT-A",
            depot_code="DPT01",
            depot_address="Jl. Depot Raya No. 1",
        )
        booking.action_create_job()

        hbl = booking.sea_job_ids[0]
        self.assertEqual(hbl.customer_ref, "CUST-REF-12345",
            msg="customer_reference Booking harus tersalin ke customer_ref HBL")
        self.assertEqual(hbl.depot_id, "DEPOT-A")
        self.assertEqual(hbl.depot_code, "DPT01")
        self.assertEqual(hbl.depot_address, "Jl. Depot Raya No. 1")

    def test_convert_copies_all_parties_and_routing(self):
        """shipper, consignee, notify, delivery agent, commodity, delivery_type, shipment_type disalin (FF-53)."""
        shipper = self.env["res.partner"].create({"name": "Shipper Test"})
        consignee = self.env["res.partner"].create({"name": "Consignee Test"})
        notify = self.env["res.partner"].create({"name": "Notify Test"})
        delivery_agent = self.env["res.partner"].create({"name": "Agent Test"})
        shipment_type = self.env["freight.shipment.type"].create({"name": "LCL / LCL"})

        booking = self._create_booking(
            shipper_id=shipper.id,
            consignee_id=consignee.id,
            notify_party_id=notify.id,
            delivery_agent_id=delivery_agent.id,
            commodity_id=self.commodity.id,
            delivery_type_id=self.delivery_type.id,
            shipment_type_id=shipment_type.id,
        )
        booking.action_create_job()

        hbl = booking.sea_job_ids[0]
        self.assertEqual(hbl.shipper_id, shipper)
        self.assertEqual(hbl.consignee_id, consignee)
        self.assertEqual(hbl.notify_party_id, notify)
        self.assertEqual(hbl.delivery_agent_id, delivery_agent)
        self.assertEqual(hbl.commodity_id, self.commodity)
        self.assertEqual(hbl.delivery_type_id, self.delivery_type)
        self.assertEqual(hbl.shipment_type_id, shipment_type)

    def test_convert_copies_canonical_vessel_routing(self):
        """FF-74: feeder/mother vessel + voyage (canonical) dari Booking
        harus tersalin ke Master saat action_create_job."""
        mother_vessel = self.env["freight.vessel"].create({
            "code": "MV002",
            "name": "Test Mother Vessel",
        })
        booking = self._create_booking(
            feeder_vessel_id=self.vessel.id,
            feeder_voyage_no="FDR-001",
            mother_vessel_id=mother_vessel.id,
            mother_voyage_no="MTR-001",
        )
        booking.action_create_job()

        master = booking.sea_job_ids[0]
        self.assertEqual(master.feeder_vessel_id, self.vessel)
        self.assertEqual(master.feeder_voyage_no, "FDR-001")
        self.assertEqual(master.mother_vessel_id, mother_vessel)
        self.assertEqual(master.mother_voyage_no, "MTR-001")

    def test_generic_vessel_fields_no_longer_exist(self):
        """FF-74: representasi generic/duplicate vessel_id, voyage_no
        (Booking) dan vessel_voy (HBL/Job) harus sudah dihapus."""
        booking = self._create_booking()
        self.assertNotIn("vessel_id", booking._fields)
        self.assertNotIn("voyage_no", booking._fields)
        self.assertNotIn("vessel_voy", self.env["freight.sea.job"]._fields)


