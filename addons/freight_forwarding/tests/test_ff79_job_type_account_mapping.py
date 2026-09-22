"""FF-79: Job Type master (klasifikasi transaksi) dan account mapping
Product/Charge Code -> account.move.line, dengan fallback ke native product
income/expense account.

Desain (revisi setelah re-evaluasi): `job_type_id` adalah Many2one STORED
biasa yang bisa dipilih/diubah manual oleh user (Change Job Type), BUKAN
computed field. Classification (business_type/freight_type/sea_ship_mode)
hanya dipakai sebagai bantuan cari kandidat + filter domain + auto-fill saat
kandidatnya tepat satu -- TIDAK diasumsikan 1:1 dengan Job Type.

Auto-fill berlaku lewat DUA jalur yang berbagi resolver yang sama
(`_get_job_type_candidates`/`_resolve_job_type_id_from_vals` di
`freight.job.type.resolver.mixin`): onchange (UI) dan `create()`
(programmatic -- Quotation -> Booking, Quotation -> Job direct, Booking ->
Create Job, dst., di mana onchange TIDAK pernah jalan).

Scope: Air Export/Import, Sea FCL/LCL Export/Import saja (tidak Consol/
Domestic/Warehouse/Local Sales, sesuai tiket)."""
import inspect

from odoo.exceptions import UserError

from .common import FreightTestBase
from ..models.master_data import job_type as job_type_module
from ..models.common import job_type_resolver_mixin as resolver_mixin_module
from ..models.master_data.acct import charge_code_account_mapping as mapping_module


class AirJobTypeTestMixin:
    """Factory kecil untuk Air Booking/Quotation, sama seperti pola lokal di
    test_air_awb_master.py -- tidak dipindah ke common.py karena hanya
    dipakai test FF-79 yang butuh Air."""

    def _create_air_booking(self, **kwargs):
        vals = {"freight_type": "export"}
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


class TestFF79JobTypeCandidates(FreightTestBase):
    """freight.job.type._get_matching_job_types() -- domain dibangun murni
    dari nilai transaksi (business_type/freight_type/sea_ship_mode), bukan
    hardcoded code. Mengembalikan SEMUA kandidat (0/1/banyak), bukan
    mengasumsikan cardinality 1:1."""

    def _create_job_type(self, code, business_type, freight_type, sea_ship_mode=False, **kwargs):
        vals = {
            "code": code,
            "name": code,
            "business_type": business_type,
            "freight_type": freight_type,
            "sea_ship_mode": sea_ship_mode,
        }
        vals.update(kwargs)
        return self.env["freight.job.type"].create(vals)

    def test_candidates_air_export_import(self):
        air_export = self._create_job_type("TST-AE", "air", "export")
        air_import = self._create_job_type("TST-AI", "air", "import")

        JobType = self.env["freight.job.type"]
        self.assertEqual(JobType._get_matching_job_types("air", "export"), air_export)
        self.assertEqual(JobType._get_matching_job_types("air", "import"), air_import)

    def test_candidates_sea_fcl_export_import(self):
        sea_fcl_export = self._create_job_type("TST-FC", "sea", "export", "fcl")
        sea_fcl_import = self._create_job_type("TST-FI", "sea", "import", "fcl")

        JobType = self.env["freight.job.type"]
        self.assertEqual(JobType._get_matching_job_types("sea", "export", "fcl"), sea_fcl_export)
        self.assertEqual(JobType._get_matching_job_types("sea", "import", "fcl"), sea_fcl_import)

    def test_candidates_sea_lcl_export_import(self):
        sea_lcl_export = self._create_job_type("TST-LC", "sea", "export", "lcl")
        sea_lcl_import = self._create_job_type("TST-LI", "sea", "import", "lcl")

        JobType = self.env["freight.job.type"]
        self.assertEqual(JobType._get_matching_job_types("sea", "export", "lcl"), sea_lcl_export)
        self.assertEqual(JobType._get_matching_job_types("sea", "import", "lcl"), sea_lcl_import)

    def test_zero_candidate(self):
        """Sea FCL Export sengaja tidak dibuat -- harus mengembalikan
        recordset kosong, bukan menebak/fallback ke code tertentu."""
        result = self.env["freight.job.type"]._get_matching_job_types("sea", "export", "fcl")
        self.assertFalse(result)

    def test_multiple_job_types_same_classification_allowed(self):
        """Cardinality klasifikasi->Job Type TIDAK 1:1 -- dua Job Type aktif
        boleh punya klasifikasi identik (mis. beda kebutuhan modul), TIDAK
        ada constraint yang memblokirnya, dan keduanya muncul sebagai
        kandidat (bukan salah satu ditolak)."""
        job_type_a = self._create_job_type("TST-DUPA", "sea", "export", "fcl")
        job_type_b = self._create_job_type("TST-DUPB", "sea", "export", "fcl")

        candidates = self.env["freight.job.type"]._get_matching_job_types("sea", "export", "fcl")
        self.assertEqual(candidates, job_type_a | job_type_b)


class TestFF79JobTypeOnchange(FreightTestBase):
    """`_onchange_job_type_classification()` di mixin Booking/Job Sea & Air:
    auto-fill HANYA saat kandidat tepat satu, kosongkan job_type_id yang
    sudah tidak cocok, dan TIDAK PERNAH menebak saat kandidat 0 atau >1."""

    def test_unique_candidate_auto_filled(self):
        job_type = self.env["freight.job.type"].create({
            "code": "TST-UNIQ1", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(freight_type="export", ship_mode="fcl", job_type_id=False)
        self.assertFalse(booking.job_type_id)

        booking._onchange_job_type_classification()
        self.assertEqual(booking.job_type_id, job_type)

    def test_zero_candidate_stays_empty(self):
        booking = self._create_booking(freight_type="import", ship_mode="lcl", job_type_id=False)
        booking._onchange_job_type_classification()
        self.assertFalse(booking.job_type_id)

    def test_multiple_candidates_stays_empty_not_arbitrary(self):
        """Kandidat >1 -- job_type_id TIDAK boleh ke-set ke salah satu
        secara arbitrer (mis. ambil `search()[0]`)."""
        job_type_a = self.env["freight.job.type"].create({
            "code": "TST-MULA", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        job_type_b = self.env["freight.job.type"].create({
            "code": "TST-MULB", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(freight_type="export", ship_mode="fcl", job_type_id=False)

        booking._onchange_job_type_classification()

        self.assertFalse(booking.job_type_id)
        self.assertIn(job_type_a, booking._get_job_type_candidates())
        self.assertIn(job_type_b, booking._get_job_type_candidates())

    def test_user_can_manually_select_one_of_valid_job_types(self):
        """Saat kandidat >1, user tetap bisa memilih salah satu Job Type
        yang valid secara manual (job_type_id adalah field stored biasa,
        bukan computed -- write langsung dihormati)."""
        job_type_a = self.env["freight.job.type"].create({
            "code": "TST-PICKA", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        self.env["freight.job.type"].create({
            "code": "TST-PICKB", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(freight_type="export", ship_mode="fcl", job_type_id=False)

        booking.job_type_id = job_type_a.id

        self.assertEqual(booking.job_type_id, job_type_a)

    def test_incompatible_job_type_cleared_on_classification_change(self):
        """job_type_id yang sudah terisi tapi tidak lagi cocok dengan
        klasifikasi baru harus dikosongkan lagi oleh onchange -- bukan
        dibiarkan menyimpan Job Type yang sudah salah klasifikasi."""
        job_type_export = self.env["freight.job.type"].create({
            "code": "TST-CLR1", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(
            freight_type="export", ship_mode="fcl", job_type_id=job_type_export.id,
        )
        self.assertEqual(booking.job_type_id, job_type_export)

        booking.freight_type = "import"
        booking._onchange_job_type_classification()

        self.assertFalse(booking.job_type_id)


class TestFF79ProgrammaticAutoFill(AirJobTypeTestMixin, FreightTestBase):
    """Auto-fill job_type_id lewat create() (jalur programmatic) -- flow
    NORMAL pembuatan Booking/Job (Quotation -> Booking, Quotation -> Job
    direct) selalu lewat Python, TIDAK pernah lewat onchange UI. Aturan
    0/1/>1 kandidat yang sama dengan onchange harus berlaku juga di sini,
    dan vals eksplisit tidak pernah ditimpa."""

    def test_sea_booking_create_with_one_candidate_auto_fills(self):
        job_type = self.env["freight.job.type"].create({
            "code": "TST-PGSEA1", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(freight_type="export", ship_mode="fcl")
        self.assertEqual(
            booking.job_type_id, job_type,
            "job_type_id harus auto-fill saat create() tanpa onchange manual",
        )

    def test_air_booking_create_with_one_candidate_auto_fills(self):
        job_type = self.env["freight.job.type"].create({
            "code": "TST-PGAIR1", "business_type": "air", "freight_type": "export",
        })
        booking = self._create_air_booking(freight_type="export")
        self.assertEqual(
            booking.job_type_id, job_type,
            "job_type_id harus auto-fill saat create() tanpa onchange manual",
        )

    def test_create_with_multiple_candidates_stays_empty(self):
        self.env["freight.job.type"].create({
            "code": "TST-PGMULA", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        self.env["freight.job.type"].create({
            "code": "TST-PGMULB", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(freight_type="export", ship_mode="fcl")
        self.assertFalse(
            booking.job_type_id,
            "Kandidat >1 tidak boleh ditebak salah satu saat create()",
        )

    def test_create_with_zero_candidates_stays_empty(self):
        booking = self._create_booking(freight_type="import", ship_mode="lcl")
        self.assertFalse(booking.job_type_id)

    def test_explicit_job_type_id_in_vals_not_overridden(self):
        """job_type_id yang eksplisit diberikan di vals HARUS dihormati,
        walau ada tepat satu kandidat lain yang berbeda."""
        matching_job_type = self.env["freight.job.type"].create({
            "code": "TST-PGEA", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        explicit_job_type = self.env["freight.job.type"].create({
            "code": "TST-PGEB", "business_type": "sea",
            "freight_type": "import", "sea_ship_mode": "lcl",
        })
        booking = self._create_booking(
            freight_type="export", ship_mode="fcl", job_type_id=explicit_job_type.id,
        )
        self.assertEqual(booking.job_type_id, explicit_job_type)
        self.assertNotEqual(booking.job_type_id, matching_job_type)


class TestFF79Propagation(AirJobTypeTestMixin, FreightTestBase):
    """Booking -> Job: job_type_id di-copy SEKALI saat create. Setelah itu
    Booking dan Job tidak live-sync -- Job boleh diubah manual (Change Job
    Type) tanpa mempengaruhi Booking, dan sebaliknya."""

    def test_booking_to_job_copies_job_type_id_once(self):
        job_type = self.env["freight.job.type"].create({
            "code": "TST-PROP1", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking = self._create_booking(
            freight_type="export", ship_mode="fcl", job_type_id=job_type.id,
        )
        result = booking.action_create_job()
        job = self.env["freight.sea.job"].browse(result["res_id"])

        self.assertEqual(job.job_type_id, job_type)

        # Setelah Job dibuat, Booking dan Job tidak live-sync.
        other_job_type = self.env["freight.job.type"].create({
            "code": "TST-PROP2", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        booking.job_type_id = other_job_type.id
        self.assertEqual(job.job_type_id, job_type, "Job tidak boleh ikut berubah saat Booking diubah")

    def test_job_job_type_id_editable_after_creation(self):
        """Change Job Type: job_type_id Job boleh ditulis ulang manual
        setelah Job dibuat."""
        job_type_a = self.env["freight.job.type"].create({
            "code": "TST-CHGA", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        job_type_b = self.env["freight.job.type"].create({
            "code": "TST-CHGB", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        job = self._create_hbl(freight_type="export", ship_mode="fcl", job_type_id=job_type_a.id)

        job.job_type_id = job_type_b.id

        self.assertEqual(job.job_type_id, job_type_b)

    def test_sea_booking_create_job_propagates_to_master_and_first_house(self):
        """Booking -> action_create_job(): Master mendapat job_type_id
        Booking, dan House PERTAMA (dibuat otomatis dari
        Booking.source_quotation_id) juga membawa job_type_id yang SAMA --
        dicopy sekali saat creation, bukan live-sync berkelanjutan."""
        job_type = self.env["freight.job.type"].create({
            "code": "TST-SHOU1", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        quotation = self._create_quotation(freight_type="export", sea_ship_mode="fcl")
        booking = self._create_booking(
            freight_type="export", ship_mode="fcl", job_type_id=job_type.id,
            quotation_id=quotation.id,
        )

        result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        house = master.house_job_ids

        self.assertEqual(master.job_type_id, job_type)
        self.assertTrue(house, "House pertama harus otomatis terbentuk dari source_quotation_id Booking")
        self.assertEqual(house.job_type_id, job_type, "House pertama harus membawa job_type_id yang sama dengan Master saat creation")

        # Tidak ada live-sync setelah creation.
        other_job_type = self.env["freight.job.type"].create({
            "code": "TST-SHOU2", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        house.job_type_id = other_job_type.id
        self.assertEqual(master.job_type_id, job_type, "Master tidak boleh ikut berubah saat House diubah manual")

    def test_air_booking_create_job_propagates_to_master_and_first_house(self):
        """Mirror test Sea di atas untuk Air Booking -> action_create_job()."""
        job_type = self.env["freight.job.type"].create({
            "code": "TST-AHOU1", "business_type": "air", "freight_type": "export",
        })
        quotation = self._create_air_quotation(freight_type="export")
        booking = self._create_air_booking(
            freight_type="export", job_type_id=job_type.id, source_quotation_id=quotation.id,
        )

        result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(result["res_id"])
        house = master.house_job_ids

        self.assertEqual(master.job_type_id, job_type)
        self.assertTrue(house, "House pertama harus otomatis terbentuk dari source_quotation_id Booking")
        self.assertEqual(house.job_type_id, job_type, "House pertama harus membawa job_type_id yang sama dengan Master saat creation")

    def test_direct_sea_quotation_to_job_uses_programmatic_auto_fill(self):
        """Direct Quotation -> Sea Job (tanpa Booking): Master & House TIDAK
        diberi job_type_id eksplisit oleh conversion method -- keduanya
        harus resolve sendiri lewat auto-fill create() (kandidat tunggal
        dari classification Job yang dibuat), bukan dari Quotation."""
        job_type = self.env["freight.job.type"].create({
            "code": "TST-DSEA1", "business_type": "sea",
            "freight_type": "import", "sea_ship_mode": "fcl",
        })
        quotation = self._create_quotation(freight_type="import", sea_ship_mode="fcl")

        result = quotation._action_convert_to_jobsheet_direct_sea()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        house = master.house_job_ids

        self.assertEqual(master.job_type_id, job_type)
        self.assertEqual(house.job_type_id, job_type)

    def test_direct_air_quotation_to_job_uses_programmatic_auto_fill(self):
        """Mirror test direct Sea di atas untuk Air."""
        job_type = self.env["freight.job.type"].create({
            "code": "TST-DAIR1", "business_type": "air", "freight_type": "import",
        })
        quotation = self._create_air_quotation(freight_type="import")

        result = quotation._action_convert_to_jobsheet_direct_air()
        master = self.env["freight.air.job"].browse(result["res_id"])
        house = master.house_job_ids

        self.assertEqual(master.job_type_id, job_type)
        self.assertEqual(house.job_type_id, job_type)


class TestFF79AccountResolver(FreightTestBase):
    """Resolver account mapping Product/Charge Code x Job Type (final,
    operasional -- dibaca langsung dari job.job_type_id, bukan resolve ulang
    dari classification) -> Sales/Cost Account, dengan fallback ke native
    product account kalau tidak ada mapping."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_type_sea_fcl_export = cls.env["freight.job.type"].create({
            "code": "TST-ACCFC", "name": "Sea FCL Export",
            "business_type": "sea", "freight_type": "export", "sea_ship_mode": "fcl",
        })
        cls.sales_account = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        cls.cost_account = cls.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        )
        cls.product_tmpl = cls.env["product.template"].create({
            "cc_item_code": "TEST-CHARGE-FF79",
            "type": "service",
            "is_charge_code": True,
        })

    def test_sales_account_mapping_resolved(self):
        self.env["freight.charge.code.account.mapping"].create({
            "product_tmpl_id": self.product_tmpl.id,
            "job_type_id": self.job_type_sea_fcl_export.id,
            "sales_account_id": self.sales_account.id,
        })
        account = self.env["freight.charge.code.account.mapping"]._resolve_account(
            self.product_tmpl, self.job_type_sea_fcl_export, "sales_account_id"
        )
        self.assertEqual(account, self.sales_account)

    def test_cost_account_mapping_resolved(self):
        self.env["freight.charge.code.account.mapping"].create({
            "product_tmpl_id": self.product_tmpl.id,
            "job_type_id": self.job_type_sea_fcl_export.id,
            "cost_account_id": self.cost_account.id,
        })
        account = self.env["freight.charge.code.account.mapping"]._resolve_account(
            self.product_tmpl, self.job_type_sea_fcl_export, "cost_account_id"
        )
        self.assertEqual(account, self.cost_account)

    def test_no_mapping_falls_back_to_native(self):
        """Tidak ada mapping Job Type-specific untuk product ini -- resolver
        mengembalikan recordset kosong, caller (sale.order.line/
        purchase.order.line) tetap pakai native property_account_income_id/
        property_account_expense_id lewat super()."""
        other_product = self.env["product.template"].create({
            "cc_item_code": "TEST-CHARGE-NO-MAPPING",
            "type": "service",
            "is_charge_code": True,
        })
        account = self.env["freight.charge.code.account.mapping"]._resolve_account(
            other_product, self.job_type_sea_fcl_export, "sales_account_id"
        )
        self.assertFalse(account)

    def test_duplicate_mapping_raises_instead_of_picking_first(self):
        """>1 mapping untuk Product + Job Type yang sama -- resolver TIDAK
        boleh diam-diam mengambil salah satu (tidak ada `limit=1`), harus
        raise error yang jelas supaya master data diperbaiki."""
        dup_product = self.env["product.template"].create({
            "cc_item_code": "TEST-CHARGE-DUP-MAPPING",
            "type": "service",
            "is_charge_code": True,
        })
        self.env["freight.charge.code.account.mapping"].create({
            "product_tmpl_id": dup_product.id,
            "job_type_id": self.job_type_sea_fcl_export.id,
            "sales_account_id": self.sales_account.id,
        })
        self.env["freight.charge.code.account.mapping"].create({
            "product_tmpl_id": dup_product.id,
            "job_type_id": self.job_type_sea_fcl_export.id,
            "sales_account_id": self.cost_account.id,
        })

        with self.assertRaises(UserError):
            self.env["freight.charge.code.account.mapping"]._resolve_account(
                dup_product, self.job_type_sea_fcl_export, "sales_account_id"
            )


class TestFF79AccountingWiring(AirJobTypeTestMixin, FreightTestBase):
    """Resolver account mapping harus benar-benar terpakai lewat wiring
    produksi (sale.order.line._prepare_invoice_line() /
    purchase.order.line._prepare_account_move_line()), bukan cuma diuji
    isolated lewat _resolve_account()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_type = cls.env["freight.job.type"].create({
            "code": "TST-WIRE1", "business_type": "sea",
            "freight_type": "export", "sea_ship_mode": "fcl",
        })
        cls.sales_account = cls.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        cls.cost_account = cls.env["account.account"].search(
            [("account_type", "=", "expense")], limit=1
        )
        cls.mapped_product = cls.env["product.template"].create({
            "cc_item_code": "TEST-CHARGE-WIRE-MAPPED",
            "type": "service",
            "is_charge_code": True,
        })
        cls.env["freight.charge.code.account.mapping"].create({
            "product_tmpl_id": cls.mapped_product.id,
            "job_type_id": cls.job_type.id,
            "sales_account_id": cls.sales_account.id,
            "cost_account_id": cls.cost_account.id,
        })
        cls.unmapped_product = cls.env["product.template"].create({
            "cc_item_code": "TEST-CHARGE-WIRE-UNMAPPED",
            "type": "service",
            "is_charge_code": True,
        })
        cls.vendor = cls.env["res.partner"].create({
            "name": "Test Vendor FF-79", "is_company": True,
        })

    def test_sale_order_line_prepare_invoice_line_uses_sales_account(self):
        job = self._create_hbl(
            freight_type="export", ship_mode="fcl", job_type_id=self.job_type.id,
        )
        order = self._create_quotation(sea_job_id=job.id)
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.mapped_product.product_variant_id.id,
            "product_uom_qty": 1.0,
            "price_unit": 100000.0,
        })

        res = line._prepare_invoice_line()

        self.assertEqual(res.get("account_id"), self.sales_account.id)

    def test_purchase_order_line_prepare_account_move_line_uses_cost_account(self):
        job = self._create_hbl(
            freight_type="export", ship_mode="fcl", job_type_id=self.job_type.id,
        )
        po = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "sea_job_id": job.id,
        })
        po_line = self.env["purchase.order.line"].create({
            "order_id": po.id,
            "product_id": self.mapped_product.product_variant_id.id,
            "product_qty": 1.0,
            "price_unit": 80000.0,
        })

        res = po_line._prepare_account_move_line()

        self.assertEqual(res.get("account_id"), self.cost_account.id)

    def test_sale_order_line_no_mapping_does_not_override_native_account(self):
        """Tidak ada mapping untuk product ini -- base
        `_prepare_invoice_line()` Odoo TIDAK pernah menyertakan key
        `account_id` (account native di-resolve belakangan lewat
        property_account_income_id/kategori produk saat invoice line
        benar-benar dibuat) -- FF-79 tidak boleh menambahkannya sendiri
        kalau tidak ada mapping."""
        job = self._create_hbl(
            freight_type="export", ship_mode="fcl", job_type_id=self.job_type.id,
        )
        order = self._create_quotation(sea_job_id=job.id)
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.unmapped_product.product_variant_id.id,
            "product_uom_qty": 1.0,
            "price_unit": 100000.0,
        })

        res = line._prepare_invoice_line()

        self.assertNotIn("account_id", res)

    def test_purchase_order_line_no_mapping_does_not_override_native_account(self):
        job = self._create_hbl(
            freight_type="export", ship_mode="fcl", job_type_id=self.job_type.id,
        )
        po = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "sea_job_id": job.id,
        })
        po_line = self.env["purchase.order.line"].create({
            "order_id": po.id,
            "product_id": self.unmapped_product.product_variant_id.id,
            "product_qty": 1.0,
            "price_unit": 80000.0,
        })

        res = po_line._prepare_account_move_line()

        self.assertNotIn("account_id", res)


class TestFF79NoHardcodedJobTypeCode(FreightTestBase):
    """Guard test: business logic FF-79 (master Job Type, resolver mixin,
    account mapping resolver) tidak boleh mengandung literal code Job Type
    seperti AE/AI/FC/FI/LC/LI."""

    FORBIDDEN_LITERALS = ('"AE"', "'AE'", '"AI"', "'AI'", '"FC"', "'FC'",
                           '"FI"', "'FI'", '"LC"', "'LC'", '"LI"', "'LI'")

    def test_no_hardcoded_job_type_codes_in_source(self):
        modules = (job_type_module, resolver_mixin_module, mapping_module)
        for module in modules:
            source = inspect.getsource(module)
            for literal in self.FORBIDDEN_LITERALS:
                self.assertNotIn(
                    literal, source,
                    "Ditemukan literal Job Type code %r di %s -- business logic "
                    "tidak boleh bergantung pada code Job Type." % (literal, module.__name__),
                )
