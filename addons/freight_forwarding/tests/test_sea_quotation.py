"""Test untuk Sea Quotation — compute fields dan actions."""
from .common import FreightTestBase


class TestSeaQuotationHblCount(FreightTestBase):
    """
    Verifikasi _compute_hbl_count yang sudah dioptimasi dari N+1 ke read_group.

    Test ini memverifikasi KEBENARAN hitungan, bukan performa.
    Performa (query count) bisa diverifikasi dengan self.assertQueryCount().
    """

    def test_hbl_count_zero_without_hbl(self):
        """Quotation tanpa booking dan HBL → hbl_count = 0."""
        quotation = self._create_quotation()
        self.assertEqual(quotation.hbl_count, 0)

    def test_hbl_count_via_booking(self):
        """HBL yang dibuat via booking di-count dengan benar."""
        quotation = self._create_quotation()
        booking = self._create_booking(quotation_id=quotation.id)

        # Buat 2 HBL via booking
        self._create_hbl(booking=booking)
        self._create_hbl(booking=booking)

        self.assertEqual(quotation.hbl_count, 2,
            msg="hbl_count harus 2 untuk 2 HBL via booking")

    def test_hbl_count_direct_import_flow(self):
        """HBL yang dibuat langsung dari quotation (import flow) di-count."""
        quotation = self._create_quotation(freight_type="import")

        # Buat HBL langsung dari quotation, tanpa booking
        self._create_hbl(quotation_id=quotation.id, freight_type="import")
        self._create_hbl(quotation_id=quotation.id, freight_type="import")

        self.assertEqual(quotation.hbl_count, 2,
            msg="hbl_count harus menghitung HBL langsung dari quotation")

    def test_hbl_count_combined_booking_and_direct(self):
        """hbl_count = HBL via booking + HBL langsung dari quotation."""
        quotation = self._create_quotation(freight_type="import")
        booking = self._create_booking(quotation_id=quotation.id)

        # 1 HBL via booking
        self._create_hbl(booking=booking)

        # 1 HBL langsung (import flow)
        self._create_hbl(quotation_id=quotation.id, freight_type="import")

        self.assertEqual(quotation.hbl_count, 2,
            msg="hbl_count harus menjumlahkan HBL dari semua sumber")

    def test_hbl_count_not_leaking_between_quotations(self):
        """HBL dari quotation A tidak masuk ke hbl_count quotation B."""
        quotation_a = self._create_quotation()
        quotation_b = self._create_quotation()

        booking_a = self._create_booking(quotation_id=quotation_a.id)
        self._create_hbl(booking=booking_a)
        self._create_hbl(booking=booking_a)

        # quotation_b tidak punya HBL apapun
        self.assertEqual(quotation_b.hbl_count, 0,
            msg="HBL dari quotation lain tidak boleh ikut terhitung")

    def test_booking_count(self):
        """booking_count dihitung benar dari relasi One2many (maksimal 1 karena unique constraint)."""
        quotation = self._create_quotation()
        self.assertEqual(quotation.booking_count, 0)

        self._create_booking(quotation_id=quotation.id)

        self.assertEqual(quotation.booking_count, 1)


class TestSeaQuotationConvertActions(FreightTestBase):
    """Test convert quotation ke booking dan HBL langsung."""

    def test_action_convert_to_booking_direct(self):
        """action_convert_to_booking_direct membuat booking dari quotation."""
        quotation = self._create_quotation()
        result = quotation.action_convert_to_booking_direct()

        new_booking = self.env["freight.sea.booking"].browse(result["res_id"])
        self.assertTrue(new_booking.exists())
        self.assertIn(quotation, new_booking.sale_order_ids)
        self.assertEqual(new_booking.freight_type, quotation.freight_type)

    def test_action_convert_to_jobsheet_direct(self):
        """action_convert_to_jobsheet_direct membuat HBL langsung (import flow)."""
        quotation = self._create_quotation(freight_type="import")
        result = quotation.action_convert_to_jobsheet_direct()

        new_hbl = self.env["freight.sea.hbl"].browse(result["res_id"])
        self.assertTrue(new_hbl.exists())
        self.assertIn(quotation, new_hbl.sale_order_ids)
        # Pastikan freight_type tidak dikonversi manual lagi
        self.assertEqual(new_hbl.freight_type, "import",
            msg="freight_type HBL harus sama persis dengan quotation (lowercase)")
        # FF-72: sea_hbl_id harus ikut ter-write-back ke quotation, bukan cuma
        # sale_order_ids milik HBL (dulu cuma bergantung ke fallback search).
        self.assertEqual(quotation.sea_hbl_id, new_hbl,
            msg="sea_hbl_id pada quotation harus menunjuk ke HBL yang baru dibuat")

    def test_action_convert_to_jobsheet_direct_writes_back_all_variants(self):
        """FF-72: sea_hbl_id harus terisi di SEMUA currency variant, bukan cuma
        quotation yang diklik convert-nya."""
        quotation = self._create_quotation(freight_type="import")
        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        result = quotation.action_convert_to_jobsheet_direct()
        new_hbl = self.env["freight.sea.hbl"].browse(result["res_id"])

        self.assertIn(quotation, new_hbl.sale_order_ids)
        self.assertIn(variant, new_hbl.sale_order_ids)
        self.assertEqual(quotation.sea_hbl_id, new_hbl,
            msg="sea_hbl_id quotation asal harus menunjuk ke HBL")
        self.assertEqual(variant.sea_hbl_id, new_hbl,
            msg="sea_hbl_id currency variant juga harus menunjuk ke HBL yang sama")
