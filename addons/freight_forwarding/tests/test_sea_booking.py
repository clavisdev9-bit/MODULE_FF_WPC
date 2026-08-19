"""Test untuk Sea Booking model."""
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger

from .common import FreightTestBase


class TestSeaBookingFields(FreightTestBase):
    """Verifikasi field constraints pada Sea Booking."""

    def test_freight_type_required(self):
        """freight_type wajib diisi — tanpanya create harus gagal."""
        with self.assertRaises(Exception,
                msg="Booking tanpa freight_type harus ditolak"):
            self.env["freight.sea.booking"].create({
                "container_type": "fcl",
                "partner_id": self.partner.id,
                "port_of_loading_id": self.port_loading.id,
                "port_of_discharge_id": self.port_discharge.id,
                "vessel_id": self.vessel.id,
                "delivery_type_id": self.delivery_type.id,
                # freight_type sengaja tidak diisi
            })

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
    """Verifikasi action_convert_to_hbl — konversi booking ke HBL."""

    def test_convert_creates_hbl(self):
        """action_convert_to_hbl membuat satu HBL baru."""
        booking = self._create_booking(freight_type="export")
        self.assertEqual(booking.hbl_count, 0)

        booking.action_convert_to_hbl()

        self.assertEqual(booking.hbl_count, 1,
            msg="Harus ada tepat 1 HBL setelah convert")

    def test_convert_hbl_inherits_freight_type(self):
        """HBL yang dibuat mewarisi freight_type dari booking — tanpa konversi manual."""
        booking_export = self._create_booking(freight_type="export")
        booking_import = self._create_booking(freight_type="import")

        booking_export.action_convert_to_hbl()
        booking_import.action_convert_to_hbl()

        hbl_export = booking_export.hbl_ids[0]
        hbl_import = booking_import.hbl_ids[0]

        # Kunci: HBL pakai casing yang sama persis (lowercase) dengan booking
        self.assertEqual(hbl_export.freight_type, "export",
            msg="HBL harus inherit 'export' langsung dari booking")
        self.assertEqual(hbl_import.freight_type, "import",
            msg="HBL harus inherit 'import' langsung dari booking")

    def test_convert_idempotent(self):
        """Memanggil action_convert_to_hbl dua kali tidak membuat HBL baru."""
        booking = self._create_booking()

        booking.action_convert_to_hbl()
        booking.action_convert_to_hbl()  # panggil lagi

        self.assertEqual(booking.hbl_count, 1,
            msg="Harus tetap 1 HBL meski convert dipanggil dua kali")

    def test_convert_copies_cargo_info(self):
        """Cargo info di booking di-copy ke HBL saat convert."""
        booking = self._create_booking()
        self._create_booking_cargo_info(booking, quantity=5)
        self._create_booking_cargo_info(booking, quantity=3)

        booking.action_convert_to_hbl()

        hbl = booking.hbl_ids[0]
        self.assertEqual(len(hbl.cargo_info_ids), 2,
            msg="Semua cargo info dari booking harus ter-copy ke HBL")

    def test_convert_returns_action_to_hbl(self):
        """action_convert_to_hbl mengembalikan action window ke HBL."""
        booking = self._create_booking()
        result = booking.action_convert_to_hbl()

        self.assertEqual(result.get("res_model"), "freight.sea.hbl",
            msg="Action harus mengarah ke model freight.sea.hbl")
        self.assertEqual(result.get("view_mode"), "form")

    def test_convert_copies_bl_info(self):
        """Field-field B/L info (termasuk notify_same_as_consignee) di-copy ke HBL saat convert."""
        booking = self._create_booking(
            consignee_id=self.partner.id,
            notify_party_id=self.partner.id,
            notify_same_as_consignee=True,
        )
        booking.action_convert_to_hbl()

        hbl = booking.hbl_ids[0]
        self.assertEqual(hbl.consignee_id, self.partner)
        self.assertEqual(hbl.notify_party_id, self.partner)
        self.assertTrue(hbl.notify_same_as_consignee)

    def test_convert_copies_shipment_type(self):
        """shipment_type_id (Many2one freight.shipment.type) tersalin otomatis ke HBL saat convert (FF-52)."""
        shipment_type = self.env["freight.shipment.type"].create({
            "name": "FCL / FCL",
        })
        booking = self._create_booking(shipment_type_id=shipment_type.id)
        booking.action_convert_to_hbl()

        hbl = booking.hbl_ids[0]
        self.assertEqual(hbl.shipment_type_id, shipment_type,
            msg="shipment_type_id harus ter-copy dari Booking ke HBL")


