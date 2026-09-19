"""Test untuk FF-73: commercial group (root quotation + currency variant)
pada Booking dan Jobsheet, lewat freight.commercial.group.mixin."""
from odoo.exceptions import ValidationError

from .common import FreightTestBase


class TestCommercialGroupBooking(FreightTestBase):
    """Booking Sea: source_quotation_id terisi saat convert, dan commercial
    group tetap live (bukan snapshot) untuk variant yang dibuat belakangan."""

    def test_source_quotation_id_set_on_convert_to_booking(self):
        quotation = self._create_quotation()
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])

        self.assertEqual(booking.source_quotation_id, quotation)
        self.assertEqual(booking._get_source_quotation(), quotation)

    def test_commercial_group_includes_variant_created_after_booking(self):
        """AC FF-73: currency variant yang dibuat SETELAH Booking terbentuk
        tetap masuk commercial group yang sama — karena _get_commercial_group()
        query live (root + root.variant_ids), bukan snapshot sale_order_ids."""
        quotation = self._create_quotation()
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])

        # Variant dibuat SETELAH booking sudah ada
        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        group = booking._get_commercial_group()
        self.assertIn(quotation, group)
        self.assertIn(variant, group,
            msg="Currency variant yang dibuat setelah Booking terbentuk harus "
                "tetap dikenali sebagai bagian commercial group yang sama")

    def test_sale_order_ids_rejects_foreign_sale_order(self):
        """AC FF-73: sale_order_ids tidak boleh terisi SO dari commercial
        group yang berbeda."""
        quotation = self._create_quotation()
        other_quotation = self._create_quotation()
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])

        with self.assertRaises(ValidationError):
            booking.write({"sale_order_ids": [(4, other_quotation.id)]})


class TestCommercialGroupJobsheet(FreightTestBase):
    """HBL Sea: dua jalur root quotation — direct-import (field sendiri) vs
    export lewat Booking (derived lewat booking_id)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Freight Forwarding Service",
            "type": "service",
            "list_price": 500000.0,
            "standard_price": 300000.0,
        })

    def test_source_quotation_id_set_on_direct_jobsheet_convert(self):
        """Import direct: Master dibuka (full operational Job, bukan shell),
        House pertamanya menyimpan source_quotation_id langsung."""
        quotation = self._create_quotation(freight_type="import")
        result = quotation.action_convert_to_jobsheet_direct()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        self.assertEqual(master.record_level, "master")
        self.assertFalse(master.source_quotation_id,
            msg="Master shell tidak menyimpan source_quotation_id sendiri")
        hbl = master.house_job_ids

        self.assertEqual(hbl.source_quotation_id, quotation)
        self.assertEqual(hbl._get_source_quotation(), quotation)

    def test_root_quotation_derived_via_booking_for_export_flow(self):
        """Export lewat Booking: HBL sendiri TIDAK menyimpan source_quotation_id
        (sengaja kosong), tapi _get_source_quotation() tetap resolve lewat
        booking_id -> booking._get_source_quotation()."""
        quotation = self._create_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])

        hbl_result = booking.action_create_job()
        hbl = self.env["freight.sea.job"].browse(hbl_result["res_id"])

        self.assertFalse(hbl.source_quotation_id,
            msg="HBL hasil export-via-booking sengaja tidak menyimpan source_quotation_id sendiri")
        self.assertEqual(hbl._get_source_quotation(), quotation,
            msg="_get_source_quotation() harus tetap resolve lewat booking_id")

    def test_commercial_group_includes_variant_created_after_jobsheet(self):
        quotation = self._create_quotation(freight_type="import")
        result = quotation.action_convert_to_jobsheet_direct()
        # FF-75: action_convert_to_jobsheet_direct membuka Master; House
        # pertamanya (yang menyimpan source_quotation_id) yang relevan untuk
        # resolusi commercial group.
        master = self.env["freight.sea.job"].browse(result["res_id"])
        hbl = master.house_job_ids

        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        group = hbl._get_commercial_group()
        self.assertIn(quotation, group)
        self.assertIn(variant, group)

    def test_sale_order_ids_rejects_foreign_sale_order(self):
        """AC FF-73: sale_order_ids Jobsheet tidak boleh terisi SO dari
        commercial group yang berbeda -- mirror test yang sama di Booking."""
        quotation = self._create_quotation(freight_type="import")
        other_quotation = self._create_quotation(freight_type="import")
        result = quotation.action_convert_to_jobsheet_direct()
        # FF-75: constraint-nya berbasis source_quotation_id -- itu ada di
        # House, bukan di Master shell (yang source_quotation_id-nya kosong).
        master = self.env["freight.sea.job"].browse(result["res_id"])
        hbl = master.house_job_ids

        with self.assertRaises(ValidationError):
            hbl.write({"sale_order_ids": [(4, other_quotation.id)]})

    def test_variant_created_after_jobsheet_syncs_analytic_and_sale_order_mirror(self):
        """AC FF-73 (skenario test minimum): Root A + Variant B, Booking ->
        Jobsheet dibuat. SETELAH Jobsheet ada, buat Variant C, tambahkan
        product line ke C. Expect: (1) C dikenali sebagai commercial group
        A dan Jobsheet resolvable dari C, (2) line baru C otomatis kebagian
        analytic_distribution 100% ke akun analitik Jobsheet TANPA perlu
        ditambahkan manual ke tab Sales Orders, (3) C otomatis masuk ke
        Booking.sale_order_ids dan Jobsheet.sale_order_ids sebagai
        compatibility mirror (source_quotation_id + variant_ids tetap source
        of truth)."""
        root = self._create_quotation()  # Root A
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: action_create_job membuka Master; House pertama (yang
        # menyimpan source_quotation_id sendiri, dan yang commercial-group
        # resolver quotation cari) otomatis dibuat sebagai child-nya.
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids
        self.assertTrue(hbl.analytic_account_id, "Jobsheet harus punya analytic account")
        self.assertIn(variant_b, booking.sale_order_ids)

        # Variant C dibuat SETELAH Booking & Jobsheet sudah ada
        variant_c_result = root.action_create_currency_variant()
        variant_c = self.env["sale.order"].browse(variant_c_result["res_id"])

        # (1) commercial group recognition + resolusi Jobsheet dari C
        self.assertIn(variant_c, hbl._get_commercial_group(),
            msg="Variant C harus dikenali sebagai bagian commercial group root A")
        self.assertEqual(
            variant_c._get_commercial_group_jobsheets("freight.sea.job"), hbl,
            msg="Jobsheet harus resolvable dari Variant C lewat commercial group",
        )

        # (2) line baru pada C otomatis kebagian analytic_distribution Jobsheet
        line = self.env["sale.order.line"].create({
            "order_id": variant_c.id,
            "product_id": self.product.id,
            "product_uom_qty": 1.0,
            "price_unit": 500000.0,
        })
        self.assertEqual(
            line.analytic_distribution,
            {str(hbl.analytic_account_id.id): 100.0},
            "Line baru pada currency variant yang dibuat SETELAH Jobsheet ada "
            "harus otomatis kebagian analytic_distribution Jobsheet, tanpa "
            "perlu ditambahkan manual ke tab Sales Orders",
        )

        # (3) compatibility mirror: C otomatis masuk sale_order_ids Booking & Jobsheet
        self.assertIn(variant_c, booking.sale_order_ids,
            msg="Variant C harus otomatis masuk ke Booking.sale_order_ids sebagai compatibility mirror")
        self.assertIn(variant_c, hbl.sale_order_ids,
            msg="Variant C harus otomatis masuk ke Jobsheet.sale_order_ids sebagai compatibility mirror")


class TestSeaCommercialGroupDownstreamNavigation(FreightTestBase):
    """FF-73 manual UAT fix: Sea child variant (B/C) harus resolve Booking &
    Jobsheet yang SAMA dengan root A -- bukan seolah belum punya downstream
    record. Air sudah benar (dipakai sebagai reference behavior); test ini
    memverifikasi Sea disamakan lewat resolver canonical FF-73
    (_get_commercial_group_bookings / _get_commercial_group_jobsheets),
    bukan booking_ids/sea_job_id milik record yang sedang dibuka."""

    def test_root_and_variants_resolve_same_booking_and_jobsheet(self):
        # Root A + Variant B, lalu convert A -> Booking X -> Jobsheet Y
        root = self._create_quotation()
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: lihat komentar setara di test_variant_created_after_jobsheet_syncs_...
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids

        # Bug 1: A dan B harus punya booking_count yang sama & resolve Booking yang sama
        self.assertEqual(root.booking_count, 1)
        self.assertEqual(variant_b.booking_count, 1,
            msg="Variant B harus mengenali Booking X yang sudah dibuat dari root A")
        self.assertEqual(
            root._get_commercial_group_bookings("freight.sea.booking"),
            variant_b._get_commercial_group_bookings("freight.sea.booking"),
        )

        # Bug 2: A dan B harus resolve Jobsheet yang sama
        self.assertEqual(root.sea_job_count, 1)
        self.assertEqual(variant_b.sea_job_count, 1)
        self.assertEqual(
            root._get_commercial_group_jobsheets("freight.sea.job"),
            variant_b._get_commercial_group_jobsheets("freight.sea.job"),
        )

        # Smart button navigation A/B harus menunjuk recordset yang sama
        action_bookings_a = root.action_view_bookings()
        action_bookings_b = variant_b.action_view_bookings()
        self.assertEqual(action_bookings_a["res_id"], booking.id)
        self.assertEqual(action_bookings_b["res_id"], booking.id)

        action_hbls_a = root.action_view_sea_jobs()
        action_hbls_b = variant_b.action_view_sea_jobs()
        self.assertEqual(action_hbls_a["res_id"], hbl.id)
        self.assertEqual(action_hbls_b["res_id"], hbl.id)

        # Buat Variant C SETELAH Booking & Jobsheet sudah ada
        variant_c_result = root.action_create_currency_variant()
        variant_c = self.env["sale.order"].browse(variant_c_result["res_id"])

        for quotation in (root, variant_b, variant_c):
            self.assertEqual(
                quotation._get_commercial_group_bookings("freight.sea.booking"),
                booking,
                msg="A/B/C harus semuanya resolve Booking X yang sama",
            )
            self.assertEqual(
                quotation._get_commercial_group_jobsheets("freight.sea.job"),
                hbl,
                msg="A/B/C harus semuanya resolve Jobsheet Y yang sama",
            )

        # Bug 3: compatibility mirror Booking & Jobsheet harus lengkap A+B+C
        self.assertEqual(
            set(booking.sale_order_ids.ids), {root.id, variant_b.id, variant_c.id},
            msg="Booking X.sale_order_ids harus berisi A+B+C",
        )
        self.assertEqual(
            set(hbl.sale_order_ids.ids), {root.id, variant_b.id, variant_c.id},
            msg="Jobsheet Y.sale_order_ids harus berisi A+B+C (tidak boleh tertinggal dari Booking)",
        )

    def test_sale_order_ids_mirror_complete_before_and_after_new_variant(self):
        """FF-73 UAT fix (Bug 3), skenario eksplisit dari manual UAT:

        Root A + Variant B -> Booking -> Jobsheet: mirror Booking & Jobsheet
        harus SUDAH lengkap A+B SEBELUM Variant C dibuat -- bukan cuma A
        (regression lama akibat guard `if not hbl.sale_order_ids`). Lalu
        Variant C dibuat: mirror keduanya harus jadi A+B+C, dan
        booking_count/sea_job_count/action_view_bookings/action_view_jobs harus
        identik di A/B/C.
        """
        root = self._create_quotation()  # A
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: lihat komentar setara di test_variant_created_after_jobsheet_syncs_...
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids

        # SEBELUM C dibuat: mirror Booking & Jobsheet harus lengkap A+B
        self.assertEqual(
            set(booking.sale_order_ids.ids), {root.id, variant_b.id},
            msg="Booking mirror harus A+B sebelum Variant C dibuat",
        )
        self.assertEqual(
            set(hbl.sale_order_ids.ids), {root.id, variant_b.id},
            msg="Jobsheet mirror harus A+B sebelum Variant C dibuat "
                "(regression lama: guard 'if not hbl.sale_order_ids' membuat "
                "Jobsheet cuma kebagian A)",
        )

        # Variant C dibuat SETELAH Booking & Jobsheet ada
        variant_c_result = root.action_create_currency_variant()
        variant_c = self.env["sale.order"].browse(variant_c_result["res_id"])

        # SETELAH C dibuat: mirror keduanya harus A+B+C
        self.assertEqual(
            set(booking.sale_order_ids.ids), {root.id, variant_b.id, variant_c.id},
            msg="Booking mirror harus A+B+C setelah Variant C dibuat",
        )
        self.assertEqual(
            set(hbl.sale_order_ids.ids), {root.id, variant_b.id, variant_c.id},
            msg="Jobsheet mirror harus A+B+C setelah Variant C dibuat",
        )

        # A/B/C harus punya booking_count & sea_job_count yang sama
        for quotation in (root, variant_b, variant_c):
            self.assertEqual(quotation.booking_count, 1)
            self.assertEqual(quotation.sea_job_count, 1)

        # A/B/C harus resolve action_view_bookings/action_view_jobs ke recordset yang sama
        for quotation in (root, variant_b, variant_c):
            action_bookings = quotation.action_view_bookings()
            action_hbls = quotation.action_view_sea_jobs()
            self.assertEqual(action_bookings["res_id"], booking.id)
            self.assertEqual(action_hbls["res_id"], hbl.id)

    def test_convert_to_booking_from_variant_does_not_create_duplicate(self):
        """Regression: memanggil action_convert_to_booking_direct dari
        Variant B setelah commercial group sudah punya Booking X TIDAK boleh
        membuat Booking kedua -- backend guard, bukan cuma visibility tombol."""
        root = self._create_quotation()
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])

        count_before = self.env["freight.sea.booking"].search_count(
            [("source_quotation_id", "=", root.id)]
        )
        second_result = variant_b.action_convert_to_booking_direct()
        count_after = self.env["freight.sea.booking"].search_count(
            [("source_quotation_id", "=", root.id)]
        )

        self.assertEqual(count_before, count_after,
            msg="Convert dari Variant B tidak boleh membuat Booking kedua untuk commercial group yang sama")
        self.assertEqual(second_result["res_id"], booking.id,
            msg="Convert dari Variant B harus mengarahkan ke Booking X yang sudah ada")


class TestCommercialGroupStaleCountRegression(FreightTestBase):
    """FF-73 UAT fix (stale non-stored compute): booking_count/sea_job_count
    (dan mirror-nya di Air, air_booking_count/air_job_count) dulu tetap 0 di
    record Variant C yang BARU dibuat, dalam transaksi/session yang sama,
    walau canonical resolver (source_quotation_id/booking_id) sudah benar --
    karena @api.depends compute field ini cuma mengacu ke field lokal C
    sendiri (booking_ids/sea_job_id/original_quotation_id), padahal nilainya
    berasal dari live search lintas record (commercial group) yang berubah
    lewat _sync_sale_order_ids_mirror() menulis field di record LAIN
    (Booking/Jobsheet), bukan di C. Test ini SENGAJA tidak browse ulang /
    reload record C -- staleness itulah yang mau dibuktikan sudah hilang."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Freight Forwarding Service",
            "type": "service",
            "list_price": 500000.0,
            "standard_price": 300000.0,
        })

    def test_variant_confirmed_after_downstream_exists_has_fresh_counts_without_reload(self):
        root = self._create_quotation()  # Root A
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: lihat komentar setara di test_variant_created_after_jobsheet_syncs_...
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids
        self.assertIn(variant_b, booking.sale_order_ids)
        self.assertIn(variant_b, hbl.sale_order_ids)

        # Variant C dibuat SETELAH Booking & Jobsheet sudah ada
        variant_c_result = root.action_create_currency_variant()
        variant_c = self.env["sale.order"].browse(variant_c_result["res_id"])
        self.env["sale.order.line"].create({
            "order_id": variant_c.id,
            "product_id": self.product.id,
            "product_uom_qty": 1.0,
            "price_unit": 500000.0,
        })

        variant_c.action_confirm()

        # Tanpa reload/re-browse variant_c: count harus langsung fresh, bukan
        # nyangkut di cache lama (0) dari sebelum sync mirror berjalan.
        self.assertEqual(
            variant_c.booking_count, 1,
            msg="Variant C harus langsung punya booking_count fresh tanpa reload "
                "setelah commercial group sync + confirm",
        )
        self.assertEqual(
            variant_c.sea_job_count, 1,
            msg="Variant C harus langsung punya sea_job_count fresh tanpa reload "
                "setelah commercial group sync + confirm",
        )
        self.assertEqual(
            variant_c._get_commercial_group_bookings("freight.sea.booking"), booking,
        )
        self.assertEqual(
            variant_c._get_commercial_group_jobsheets("freight.sea.job"), hbl,
        )

        # Root A & Variant B (member group lama) juga harus tetap fresh.
        for quotation in (root, variant_b):
            self.assertEqual(quotation.booking_count, 1)
            self.assertEqual(quotation.sea_job_count, 1)

    def test_air_variant_confirmed_after_downstream_exists_has_fresh_counts_without_reload(self):
        """Mirror test Sea di atas, untuk Air: _invalidate_commercial_group_downstream_counts()
        sekarang juga meng-invalidasi air_booking_count/air_job_count, jadi Variant C
        (Air) harus langsung fresh tanpa reload, sama seperti Sea."""
        root = self._create_quotation(freight_business_type="air")  # Root A
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        hawb_result = booking.action_create_job()
        # FF-75: action_create_job (Air) membuka Master; House pertama (yang
        # menyimpan source_quotation_id sendiri) otomatis dibuat sebagai child-nya.
        master_hawb = self.env["freight.air.job"].browse(hawb_result["res_id"])
        hawb = master_hawb.house_job_ids
        self.assertIn(variant_b, booking.sale_order_ids)
        self.assertIn(variant_b, hawb.sale_order_ids)

        # Variant C dibuat SETELAH Booking & Jobsheet sudah ada
        variant_c_result = root.action_create_currency_variant()
        variant_c = self.env["sale.order"].browse(variant_c_result["res_id"])

        # Tanpa reload/re-browse variant_c: count harus langsung fresh.
        self.assertEqual(
            variant_c.air_booking_count, 1,
            msg="Variant C (Air) harus langsung punya air_booking_count fresh "
                "tanpa reload setelah commercial group sync",
        )
        self.assertEqual(
            variant_c.air_job_count, 1,
            msg="Variant C (Air) harus langsung punya air_job_count fresh "
                "tanpa reload setelah commercial group sync",
        )
        self.assertEqual(
            variant_c._get_commercial_group_bookings("freight.air.booking"), booking,
        )
        self.assertEqual(
            variant_c._get_commercial_group_jobsheets("freight.air.job"), hawb,
        )

        # Action resolver Booking/Jobsheet dari Variant C harus tetap
        # menunjuk record existing (bukan res_id kosong / bukan Booking baru).
        action_bookings_c = variant_c.action_convert_to_booking_direct()
        action_hawbs_c = variant_c.action_view_air_jobs()
        self.assertEqual(action_bookings_c["res_id"], booking.id)
        self.assertEqual(action_hawbs_c["res_id"], hawb.id)


class TestSeaCommercialGroupLocalMirror(FreightTestBase):
    """FF-73 UAT fix (Masalah 2): booking_ids/sea_job_ids pada sale.order Sea
    sekarang jadi compatibility mirror -- ditulis eksplisit ke field lokal
    (bukan cuma sale_order_ids milik Booking/Jobsheet), parity dengan
    air_booking_ids milik Air, supaya currency variant yang dibuat SETELAH
    Booking & Jobsheet ada langsung "mengenali" relasi lewat field sendiri."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Freight Forwarding Service",
            "type": "service",
            "list_price": 500000.0,
            "standard_price": 300000.0,
        })

    def test_variant_created_after_downstream_has_local_mirror_and_fresh_counts(self):
        # A + B -> Booking -> Jobsheet
        root = self._create_quotation()  # A
        variant_b_result = root.action_create_currency_variant()
        variant_b = self.env["sale.order"].browse(variant_b_result["res_id"])

        booking_result = root.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        hbl_result = booking.action_create_job()
        # FF-75: lihat komentar setara di test_variant_created_after_jobsheet_syncs_...
        master = self.env["freight.sea.job"].browse(hbl_result["res_id"])
        hbl = master.house_job_ids

        # create C SETELAH Booking & Jobsheet ada
        variant_c_result = root.action_create_currency_variant()
        variant_c = self.env["sale.order"].browse(variant_c_result["res_id"])

        # Canonical resolver C -> Booking existing (tidak berubah, tetap benar)
        self.assertEqual(
            variant_c._get_commercial_group_bookings("freight.sea.booking"), booking,
            msg="Canonical resolver C harus tetap resolve ke Booking existing",
        )
        # Compatibility mirror: C.booking_ids berisi Booking existing
        self.assertIn(booking, variant_c.booking_ids,
            msg="C.booking_ids harus merepresentasikan Booking canonical sebagai compatibility mirror")
        self.assertIn(hbl, variant_c.sea_job_ids,
            msg="C.sea_job_ids harus merepresentasikan Jobsheet canonical sebagai compatibility mirror")

        self.env["sale.order.line"].create({
            "order_id": variant_c.id,
            "product_id": self.product.id,
            "product_uom_qty": 1.0,
            "price_unit": 500000.0,
        })
        variant_c.action_confirm()

        self.assertGreater(variant_c.booking_count, 0,
            msg="C.booking_count harus > 0 setelah Confirm")
        self.assertGreater(variant_c.sea_job_count, 0,
            msg="C.sea_job_count harus > 0 setelah Confirm")


class TestAirExportJobsheetSmartButton(FreightTestBase):
    """FF-73 UAT fix (Masalah 1): Air Export dengan Jobsheet (HAWB) harus
    punya air_job_count > 0 -- smart button Jobsheet di quotation.xml sebelumnya
    dibatasi freight_type == 'import' sehingga Export tidak pernah bisa
    menampilkannya walau air_job_count sudah benar. Test ini memverifikasi sisi
    model (air_job_count); visibility XML diverifikasi langsung lewat perubahan
    views/air/sales/quotation.xml (invisible domain tidak lagi mengecek
    freight_type untuk action_view_jobs)."""

    def test_air_export_jobsheet_hawb_count_positive(self):
        """FF-75: action_create_job (Booking Export) sekarang membuat 1 Master
        (dibuka oleh action, res_id) + 1 House pertama otomatis dari
        Booking.source_quotation_id. Komersial-group resolver quotation
        harus resolve ke House tersebut (yang menyimpan source_quotation_id
        sendiri) -- BUKAN ke Master shell yang dibuka oleh action."""
        quotation = self._create_quotation(freight_business_type="air", freight_type="export")
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        hawb_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(hawb_result["res_id"])
        house = master.house_job_ids

        self.assertTrue(house, msg="House pertama harus otomatis dibuat dari source_quotation_id Booking")
        self.assertGreater(quotation.air_job_count, 0,
            msg="Air Export quotation dengan Jobsheet harus punya air_job_count > 0")
        self.assertEqual(
            quotation._get_commercial_group_jobsheets("freight.air.job"), house,
        )
