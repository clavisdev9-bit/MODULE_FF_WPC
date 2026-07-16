"""Test untuk logika kalkulasi volume di FreightCargoInfoMixin."""
from .common import FreightTestBase


class TestCargoInfoVolume(FreightTestBase):
    """
    Verifikasi logika kalkulasi volume otomatis di cargo_info_mixin.

    Ini adalah unit test untuk helper _recalculate_volume() yang sebelumnya
    duplikat di dua onchange — sekarang sudah dikonsolidasi.
    """

    def setUp(self):
        super().setUp()
        self.booking = self._create_booking()
        self.cargo = self._create_booking_cargo_info(self.booking, uom="box")

    # ------------------------------------------------------------------
    # Volume calculation
    # ------------------------------------------------------------------

    def test_volume_calculated_from_dimensions(self):
        """Volume dihitung otomatis: CBM = (L × W × H) ÷ 1.000.000."""
        # Arrange
        self.cargo.write({
            "length": 100.0,  # cm
            "width": 50.0,    # cm
            "height": 40.0,   # cm
            "volume_manual": False,
        })

        # Act — trigger onchange via internal call (setUpClass tidak trigger onchange)
        self.cargo._onchange_volume()

        # Assert: 100 × 50 × 40 / 1_000_000 = 0.2 CBM
        self.assertAlmostEqual(self.cargo.volume, 0.2, places=6,
            msg="Volume harus 0.2 CBM untuk dimensi 100×50×40 cm")

    def test_volume_zero_when_dimension_missing(self):
        """Volume = 0 jika salah satu dimensi tidak diisi."""
        self.cargo.write({
            "length": 100.0,
            "width": 50.0,
            "height": 0.0,       # kosong
            "volume_manual": False,
        })
        self.cargo._onchange_volume()

        self.assertEqual(self.cargo.volume, 0.0,
            msg="Volume harus 0 jika height kosong")

    def test_volume_not_recalculated_when_manual(self):
        """Saat volume_manual=True, _onchange_volume tidak mengubah volume."""
        self.cargo.write({
            "length": 100.0,
            "width": 50.0,
            "height": 40.0,
            "volume": 99.9,      # set manual
            "volume_manual": True,
        })
        self.cargo._onchange_volume()

        self.assertAlmostEqual(self.cargo.volume, 99.9, places=1,
            msg="Volume manual tidak boleh di-override oleh onchange")

    def test_volume_recalculated_when_manual_toggled_off(self):
        """Saat volume_manual di-toggle ke False, volume di-recalculate."""
        self.cargo.write({
            "length": 200.0,
            "width": 100.0,
            "height": 50.0,
            "volume": 99.9,
            "volume_manual": True,
        })
        # Toggle off
        self.cargo.volume_manual = False
        self.cargo._onchange_volume_manual()

        # 200 × 100 × 50 / 1_000_000 = 1.0 CBM
        self.assertAlmostEqual(self.cargo.volume, 1.0, places=6,
            msg="Volume harus di-recalculate saat volume_manual dimatikan")

    def test_recalculate_volume_helper_consistent(self):
        """_recalculate_volume() menghasilkan hasil yang sama dengan manual formula."""
        self.cargo.write({
            "length": 60.0,
            "width": 40.0,
            "height": 30.0,
            "volume_manual": False,
        })
        self.cargo._recalculate_volume()

        expected = (60.0 * 40.0 * 30.0) / 1_000_000
        self.assertAlmostEqual(self.cargo.volume, expected, places=6)
