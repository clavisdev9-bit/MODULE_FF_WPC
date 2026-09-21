"""Test untuk Sea Quotation — compute fields dan actions."""
from .common import FreightTestBase


class TestSeaQuotationHblCount(FreightTestBase):
    """
    Verifikasi _compute_hbl_count yang sudah dioptimasi dari N+1 ke read_group.

    Test ini memverifikasi KEBENARAN hitungan, bukan performa.
    Performa (query count) bisa diverifikasi dengan self.assertQueryCount().
    """

    def test_hbl_count_zero_without_hbl(self):
        """Quotation tanpa booking dan HBL → sea_job_count = 0."""
        quotation = self._create_quotation()
        self.assertEqual(quotation.sea_job_count, 0)

    def test_hbl_count_via_booking(self):
        """FF-75: House yang tergabung ke Master (dari Booking) di-count
        dengan benar. Setiap House menyimpan source_quotation_id sendiri --
        resolver commercial group tidak lagi mengikuti booking_id.source_quotation_id
        (lihat _get_commercial_group_jobsheets)."""
        quotation = self._create_quotation()
        booking = self._create_booking(quotation_id=quotation.id)
        master = self._create_hbl(booking=booking, record_level="master", ship_mode="lcl")

        # Buat 2 House, digabung ke Master
        self._create_hbl(quotation_id=quotation.id, master_job_id=master.id)
        self._create_hbl(quotation_id=quotation.id, master_job_id=master.id)

        self.assertEqual(quotation.sea_job_count, 2,
            msg="sea_job_count harus 2 untuk 2 House yang tergabung ke Master")

    def test_hbl_count_direct_import_flow(self):
        """HBL yang dibuat langsung dari quotation (import flow) di-count."""
        quotation = self._create_quotation(freight_type="import")

        # Buat HBL langsung dari quotation, tanpa booking
        self._create_hbl(quotation_id=quotation.id, freight_type="import")
        self._create_hbl(quotation_id=quotation.id, freight_type="import")

        self.assertEqual(quotation.sea_job_count, 2,
            msg="sea_job_count harus menghitung HBL langsung dari quotation")

    def test_hbl_count_combined_booking_and_direct(self):
        """FF-75: sea_job_count = House tergabung Master (dari Booking) +
        House langsung dari quotation (tanpa Master)."""
        quotation = self._create_quotation(freight_type="import")
        booking = self._create_booking(quotation_id=quotation.id)
        master = self._create_hbl(booking=booking, record_level="master")

        # 1 House tergabung ke Master (dari Booking)
        self._create_hbl(quotation_id=quotation.id, master_job_id=master.id)

        # 1 Job langsung dari quotation (import flow), tanpa Master
        self._create_hbl(quotation_id=quotation.id, freight_type="import")

        self.assertEqual(quotation.sea_job_count, 2,
            msg="sea_job_count harus menjumlahkan HBL dari semua sumber")

    def test_hbl_count_not_leaking_between_quotations(self):
        """HBL dari quotation A tidak masuk ke sea_job_count quotation B."""
        quotation_a = self._create_quotation()
        quotation_b = self._create_quotation()

        booking_a = self._create_booking(quotation_id=quotation_a.id)
        self._create_hbl(booking=booking_a)
        self._create_hbl(booking=booking_a)

        # quotation_b tidak punya HBL apapun
        self.assertEqual(quotation_b.sea_job_count, 0,
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
        """FF-75: action_convert_to_jobsheet_direct (Import) membuat 1 Master
        Job penuh (bukan shell -- tetap freight_type-nya sendiri, bisa
        dioperasikan normal) + 1 House pertama yang membawa link quotation."""
        quotation = self._create_quotation(freight_type="import")
        result = quotation.action_convert_to_jobsheet_direct()

        master = self.env["freight.sea.job"].browse(result["res_id"])
        self.assertTrue(master.exists())
        self.assertEqual(master.record_level, "master")
        # Master bukan shell kosong -- field operasionalnya sendiri terisi
        # dan tetap Job penuh yang bisa dipakai/diedit normal.
        self.assertEqual(master.freight_type, "import")
        self.assertTrue(master.analytic_account_id,
            msg="Master harus tetap punya analytic account canonical sendiri")

        new_hbl = master.house_job_ids
        self.assertTrue(new_hbl, msg="House pertama harus otomatis dibuat di bawah Master")
        self.assertIn(quotation, new_hbl.sale_order_ids)
        # Pastikan freight_type tidak dikonversi manual lagi
        self.assertEqual(new_hbl.freight_type, "import",
            msg="freight_type HBL harus sama persis dengan quotation (lowercase)")
        # FF-72: sea_job_id harus ikut ter-write-back ke quotation, bukan cuma
        # sale_order_ids milik HBL (dulu cuma bergantung ke fallback search).
        self.assertEqual(quotation.sea_job_id, new_hbl,
            msg="sea_job_id pada quotation harus menunjuk ke House yang baru dibuat")

    def test_action_convert_to_jobsheet_direct_writes_back_all_variants(self):
        """FF-72: sea_job_id harus terisi di SEMUA currency variant, bukan cuma
        quotation yang diklik convert-nya."""
        quotation = self._create_quotation(freight_type="import")
        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        result = quotation.action_convert_to_jobsheet_direct()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        new_hbl = master.house_job_ids

        self.assertIn(quotation, new_hbl.sale_order_ids)
        self.assertIn(variant, new_hbl.sale_order_ids)
        self.assertEqual(quotation.sea_job_id, new_hbl,
            msg="sea_job_id quotation asal harus menunjuk ke HBL")
        self.assertEqual(variant.sea_job_id, new_hbl,
            msg="sea_job_id currency variant juga harus menunjuk ke HBL yang sama")
