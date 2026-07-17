"""
Reproduction test untuk bug yang diperbaiki di booking_convert_wizard.

BUG #1: _prepare_booking_cargo_info_vals mengakses .package_type (typo)
        seharusnya .package_type_id — crash saat field Many2one kosong.
BUG #2: Tidak ada None-check pada container_type_id dan types_of_cargo.

Test di file ini HARUS gagal pada kode lama, dan LULUS setelah perbaikan.
"""
from .common import FreightTestBase


class TestBookingConvertWizardCargoVals(FreightTestBase):
    """
    Reproduce test untuk bug field name di _prepare_booking_cargo_info_vals.

    Sebelum fix: cargo dengan package_type_id=False akan crash karena
    wizard mengakses .package_type.id pada field yang tidak ada.
    """

    def setUp(self):
        super().setUp()
        self.quotation = self._create_quotation()
        self.booking = self._create_booking(quotation_id=self.quotation.id)

    def _create_quotation_cargo(self, quotation, **kwargs):
        """Helper: buat cargo info pada quotation."""
        vals = {
            "quotation_id": quotation.id,
            "uom": "box",
            "quantity": 1,
        }
        vals.update(kwargs)
        return self.env["freight.sea.quotation.cargo.info"].create(vals)

    # ------------------------------------------------------------------
    # Bug Reproduction Tests (Prove-It Pattern)
    # ------------------------------------------------------------------

    def test_wizard_cargo_copy_without_package_type(self):
        """
        [BUG REPRODUCTION] Cargo tanpa package_type_id tidak crash saat copy.

        Sebelum fix: mengakses `cargo_info.package_type.id` → AttributeError
        Setelah fix: mengakses `cargo_info.package_type_id.id if ... else False`
        """
        # Arrange: cargo tanpa package_type_id (kasus umum — field opsional)
        cargo = self._create_quotation_cargo(
            self.quotation,
            package_type_id=False,
            container_type_id=False,
            types_of_cargo=False,
        )

        wizard = self.env["freight.sea.booking.convert.wizard"].create({
            "quotation_id": self.quotation.id,
            "vessel_id": self.vessel.id,
            "voyage_no": "V001",
            "freight_type": "export",
        })

        # Act — ini yang dulu crash
        try:
            vals = wizard._prepare_booking_cargo_info_vals(cargo, self.booking)
        except AttributeError as e:
            self.fail(f"_prepare_booking_cargo_info_vals crash dengan AttributeError: {e}")

        # Assert: semua field yang kosong harus False, bukan error
        self.assertFalse(vals.get("package_type_id"),
            msg="package_type_id harus False saat field kosong")
        self.assertFalse(vals.get("container_type_id"),
            msg="container_type_id harus False saat field kosong")
        self.assertFalse(vals.get("types_of_cargo"),
            msg="types_of_cargo harus False saat field kosong")

    def test_wizard_cargo_copy_with_all_fields(self):
        """Cargo dengan semua field terisi ter-copy dengan benar ke booking."""
        # Arrange
        cargo = self._create_quotation_cargo(
            self.quotation,
            quantity=5,
            gross_weight=1000.0,
            net_weight=900.0,
            container_type_id=self.container_type.id,
        )

        wizard = self.env["freight.sea.booking.convert.wizard"].create({
            "quotation_id": self.quotation.id,
            "vessel_id": self.vessel.id,
            "voyage_no": "V001",
            "freight_type": "export",
        })

        # Act
        vals = wizard._prepare_booking_cargo_info_vals(cargo, self.booking)

        # Assert: semua nilai ter-copy benar
        self.assertEqual(vals["booking_id"], self.booking.id)
        self.assertEqual(vals["quantity"], 5)
        self.assertAlmostEqual(vals["gross_weight"], 1000.0)
        self.assertAlmostEqual(vals["net_weight"], 900.0)
        self.assertEqual(vals["container_type_id"], self.container_type.id)

    def test_wizard_full_convert_creates_booking_with_cargo(self):
        """action_convert_to_booking via wizard membuat booking dengan cargo ter-copy."""
        # Arrange: quotation dengan 2 cargo
        self._create_quotation_cargo(self.quotation, quantity=3)
        self._create_quotation_cargo(self.quotation, quantity=7)

        wizard = self.env["freight.sea.booking.convert.wizard"].with_context(
            active_id=self.quotation.id
        ).create({
            "quotation_id": self.quotation.id,
            "vessel_id": self.vessel.id,
            "voyage_no": "V001",
            "freight_type": "export",
        })

        # Act
        result = wizard.action_convert_to_booking()

        # Assert: booking dibuat dengan cargo
        new_booking = self.env["freight.sea.booking"].browse(result["res_id"])
        self.assertTrue(new_booking.exists(), msg="Booking harus berhasil dibuat")
        self.assertEqual(len(new_booking.cargo_info_ids), 2,
            msg="Kedua cargo harus ter-copy ke booking baru")
