"""FF-73 follow-up: regression test untuk migrations/18.0.1.8/post-migrate.py.

Migration lama memilih root secara arbitrer (MIN(sale_order_id)). Test ini
memverifikasi logic baru: root hanya diisi kalau SELURUH anggota
sale_order_ids resolve ke EXACTLY satu root (COALESCE(original_quotation_id,
id)); kalau tidak ada anggota, atau anggota resolve ke >1 root berbeda,
root_quotation_id harus tetap kosong -- TIDAK ada pilihan arbitrer.

Juga memverifikasi migration melengkapi compatibility mirror (sale_order_ids)
supaya berisi SELURUH commercial group (root + seluruh variant-nya) begitu
root berhasil di-resolve dengan aman -- bukan cuma anggota yang sudah ada
sebelum migration.

Data legacy disimulasikan lewat ORM langsung (create Booking/HBL dengan
sale_order_ids terisi TAPI root_quotation_id sengaja dibiarkan kosong --
persis kondisi sebelum FF-73/kolom root_quotation_id ada), lalu memanggil
migrate() yang sesungguhnya di atas cursor test yang realistis (Postgres
sungguhan, bukan mock)."""
import importlib.util
import os

from .common import FreightTestBase

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "migrations", "18.0.1.8", "post-migrate.py",
)


def _load_post_migrate_module():
    spec = importlib.util.spec_from_file_location(
        "freight_forwarding_ff73_post_migrate_18_0_1_8", _MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestResolveSingleRootPureLogic(FreightTestBase):
    """Unit test murni untuk helper resolve_single_root() -- tidak butuh DB."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_migrate = _load_post_migrate_module()

    def test_single_root_resolves(self):
        self.assertEqual(self.post_migrate.resolve_single_root([1, 1, 1]), 1)

    def test_conflicting_roots_returns_none(self):
        self.assertIsNone(self.post_migrate.resolve_single_root([1, 2]))

    def test_empty_returns_none(self):
        self.assertIsNone(self.post_migrate.resolve_single_root([]))

    def test_none_values_ignored(self):
        self.assertEqual(self.post_migrate.resolve_single_root([1, None]), 1)


class TestSeaBookingMigrationRegression(FreightTestBase):
    """4 skenario wajib (FF-73 follow-up item 3), untuk freight.sea.booking."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_migrate = _load_post_migrate_module()

    def _run_migration(self):
        self.post_migrate.migrate(self.env.cr, "18.0.1.8")
        self.env.invalidate_all()

    def test_scenario_1_sale_order_ids_root_and_variant_resolves_root_and_completes_mirror(self):
        """sale_order_ids = [A, B], B variant A -> root = A, mirror = A+B."""
        root = self._create_quotation()  # A
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])  # B

        booking = self.env["freight.sea.booking"].create({
            "sale_order_ids": [(6, 0, [root.id, variant.id])],
        })
        self.assertFalse(booking.root_quotation_id)

        self._run_migration()

        self.assertEqual(booking.root_quotation_id, root)
        self.assertEqual(set(booking.sale_order_ids.ids), {root.id, variant.id})

    def test_scenario_2_sale_order_ids_only_variant_resolves_root_and_adds_root_to_mirror(self):
        """sale_order_ids hanya [B], B variant A -> root = A, mirror = A+B
        (migration harus MENAMBAHKAN A ke mirror, bukan cuma membaca root)."""
        root = self._create_quotation()  # A
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])  # B

        booking = self.env["freight.sea.booking"].create({
            "sale_order_ids": [(6, 0, [variant.id])],
        })
        self.assertFalse(booking.root_quotation_id)
        self.assertNotIn(root, booking.sale_order_ids)

        self._run_migration()

        self.assertEqual(booking.root_quotation_id, root)
        self.assertEqual(set(booking.sale_order_ids.ids), {root.id, variant.id})

    def test_scenario_3_two_different_roots_leaves_root_empty_no_canonicalization(self):
        """sale_order_ids = [A, X], A dan X dua root berbeda -> root TIDAK
        diisi, tidak ada arbitrary canonicalization (dulu: MIN(sale_order_id))."""
        root_a = self._create_quotation()  # A (root)
        root_x = self._create_quotation()  # X (root lain, tidak ada hubungan)

        booking = self.env["freight.sea.booking"].create({
            "sale_order_ids": [(6, 0, [root_a.id, root_x.id])],
        })
        self.assertFalse(booking.root_quotation_id)

        self._run_migration()

        self.assertFalse(
            booking.root_quotation_id,
            msg="Booking dengan sale_order_ids yang resolve ke >1 root harus "
                "TETAP kosong -- tidak boleh diam-diam pilih A atau X",
        )
        # Mirror TIDAK boleh berubah -- tidak ada normalisasi tanpa root yang aman.
        self.assertEqual(set(booking.sale_order_ids.ids), {root_a.id, root_x.id})

    def test_scenario_4_no_sale_order_ids_leaves_root_empty(self):
        """sale_order_ids kosong -> root_quotation_id tetap kosong."""
        booking = self.env["freight.sea.booking"].create({})
        self.assertFalse(booking.root_quotation_id)
        self.assertFalse(booking.sale_order_ids)

        self._run_migration()

        self.assertFalse(booking.root_quotation_id)
        self.assertFalse(booking.sale_order_ids)

    def test_migration_is_idempotent(self):
        """Menjalankan migrate() dua kali tidak mengubah hasil kedua kalinya."""
        root = self._create_quotation()  # A
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])  # B

        booking = self.env["freight.sea.booking"].create({
            "sale_order_ids": [(6, 0, [variant.id])],
        })

        self._run_migration()
        first_root = booking.root_quotation_id
        first_mirror = set(booking.sale_order_ids.ids)

        self._run_migration()

        self.assertEqual(booking.root_quotation_id, first_root)
        self.assertEqual(set(booking.sale_order_ids.ids), first_mirror)


class TestSeaJobsheetDirectMigrationRegression(FreightTestBase):
    """Aturan yang sama diterapkan untuk Jobsheet direct (booking_id IS NULL).
    Jobsheet DENGAN booking_id terisi harus dilewati (tidak disentuh)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_migrate = _load_post_migrate_module()

    def _run_migration(self):
        self.post_migrate.migrate(self.env.cr, "18.0.1.8")
        self.env.invalidate_all()

    def test_direct_jobsheet_resolves_single_root_and_completes_mirror(self):
        root = self._create_quotation(freight_type="import")  # A
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])  # B

        hbl = self.env["freight.sea.hbl"].create({
            "sale_order_ids": [(6, 0, [variant.id])],
        })
        self.assertFalse(hbl.root_quotation_id)

        self._run_migration()

        self.assertEqual(hbl.root_quotation_id, root)
        self.assertEqual(set(hbl.sale_order_ids.ids), {root.id, variant.id})

    def test_jobsheet_with_booking_id_is_skipped_even_if_ambiguous(self):
        """Jobsheet export-via-booking (booking_id terisi) TIDAK boleh
        disentuh migration, apapun isi sale_order_ids-nya -- root-nya
        didapat lewat Booking, bukan disimpan dobel di Jobsheet."""
        booking = self.env["freight.sea.booking"].create({})
        root_a = self._create_quotation()
        root_x = self._create_quotation()

        hbl = self.env["freight.sea.hbl"].create({
            "booking_id": booking.id,
            "sale_order_ids": [(6, 0, [root_a.id, root_x.id])],
        })
        self.assertFalse(hbl.root_quotation_id)

        self._run_migration()

        self.assertFalse(
            hbl.root_quotation_id,
            msg="Jobsheet dengan booking_id terisi tidak boleh mendapat "
                "root_quotation_id sendiri dari migration",
        )


class TestJobsheetViaBookingMigrationMirrorRegression(FreightTestBase):
    """Gap follow-up: Jobsheet Export legacy yang dibuat lewat Booking
    (booking_id terisi) SEBELUMNYA dilewati SELURUHNYA oleh
    _backfill_and_normalize (extra_filter booking_id IS NULL) -- termasuk
    normalisasi compatibility mirror sale_order_ids-nya, padahal Booking-nya
    sendiri sudah benar di-resolve & di-normalisasi. Fix: mirror sale_order_ids
    Jobsheet-via-Booking ikut dinormalisasi ke root Booking (via
    _normalize_jobsheet_mirror_via_booking, dipakai generic untuk Sea & Air),
    root_quotation_id Jobsheet TETAP tidak disentuh (root tetap derived lewat
    Booking, bukan disimpan dobel)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_migrate = _load_post_migrate_module()

    def _run_migration(self):
        self.post_migrate.migrate(self.env.cr, "18.0.1.8")
        self.env.invalidate_all()

    def test_sea_jobsheet_via_booking_mirror_normalized_to_booking_root(self):
        """Root A + Variant B. Legacy Booking X: root_quotation_id=NULL,
        sale_order_ids=[A]. Legacy Jobsheet J: booking_id=X,
        root_quotation_id=NULL, sale_order_ids=[A].

        Expected setelah migration:
        - Booking X.root_quotation_id == A, Booking X.sale_order_ids == {A,B}
        - Jobsheet J.root_quotation_id tetap False (derived lewat Booking)
        - Jobsheet J.booking_id tetap X
        - Jobsheet J.sale_order_ids == {A,B} (dinormalisasi ke root Booking)
        """
        root = self._create_quotation()  # A
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])  # B

        booking = self.env["freight.sea.booking"].create({
            "sale_order_ids": [(6, 0, [root.id])],
        })
        jobsheet = self.env["freight.sea.hbl"].create({
            "booking_id": booking.id,
            "sale_order_ids": [(6, 0, [root.id])],
        })
        self.assertFalse(booking.root_quotation_id)
        self.assertFalse(jobsheet.root_quotation_id)

        self._run_migration()

        self.assertEqual(booking.root_quotation_id, root,
            msg="Booking X harus resolve root_quotation_id = A")
        self.assertEqual(set(booking.sale_order_ids.ids), {root.id, variant.id},
            msg="Booking X.sale_order_ids harus dinormalisasi jadi {A, B}")

        self.assertFalse(jobsheet.root_quotation_id,
            msg="Jobsheet via Booking TIDAK boleh diberi root_quotation_id sendiri")
        self.assertEqual(jobsheet.booking_id, booking,
            msg="Jobsheet.booking_id tidak boleh berubah")
        self.assertEqual(set(jobsheet.sale_order_ids.ids), {root.id, variant.id},
            msg="Jobsheet J.sale_order_ids harus dinormalisasi ke full commercial "
                "group root Booking (A+B), bukan cuma dilewati")

    def test_sea_jobsheet_via_ambiguous_booking_mirror_not_touched(self):
        """Kalau Booking-nya sendiri TIDAK resolve (ambigu/kosong), Jobsheet
        via Booking itu juga TIDAK boleh ditebak/disentuh mirror-nya."""
        root_a = self._create_quotation()
        root_x = self._create_quotation()

        booking = self.env["freight.sea.booking"].create({
            "sale_order_ids": [(6, 0, [root_a.id, root_x.id])],  # ambigu
        })
        jobsheet = self.env["freight.sea.hbl"].create({
            "booking_id": booking.id,
            "sale_order_ids": [(6, 0, [root_a.id])],
        })

        self._run_migration()

        self.assertFalse(booking.root_quotation_id)
        self.assertFalse(jobsheet.root_quotation_id)
        self.assertEqual(
            set(jobsheet.sale_order_ids.ids), {root_a.id},
            msg="Mirror Jobsheet tidak boleh berubah kalau Booking-nya sendiri tidak resolve",
        )

    def test_air_jobsheet_via_booking_mirror_normalized_to_booking_root(self):
        """Mirror test Air: code path generic dan identik dengan Sea --
        _normalize_jobsheet_mirror_via_booking() dipanggil dua kali di
        migrate() dengan argumen table/rel_table/fk_col yang berbeda, tapi
        logic-nya (fetch resolved booking roots -> normalize jobsheet mirror
        lewat _normalize_commercial_group_mirror yang sama) sama sekali tidak
        di-percabangkan per business type. Test ini tetap ditambahkan (bukan
        cuma mengandalkan penjelasan) supaya regresi spesifik Air (misal typo
        nama tabel/kolom Air) tetap tertangkap."""
        root = self.env["sale.order"].create({
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        })  # A
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])  # B

        booking = self.env["freight.air.booking"].create({
            "sale_order_ids": [(6, 0, [root.id])],
        })
        hawb = self.env["freight.air.hawb"].create({
            "booking_id": booking.id,
            "sale_order_ids": [(6, 0, [root.id])],
        })
        self.assertFalse(booking.root_quotation_id)
        self.assertFalse(hawb.root_quotation_id)

        self._run_migration()

        self.assertEqual(booking.root_quotation_id, root)
        self.assertEqual(set(booking.sale_order_ids.ids), {root.id, variant.id})
        self.assertFalse(hawb.root_quotation_id)
        self.assertEqual(hawb.booking_id, booking)
        self.assertEqual(set(hawb.sale_order_ids.ids), {root.id, variant.id})
