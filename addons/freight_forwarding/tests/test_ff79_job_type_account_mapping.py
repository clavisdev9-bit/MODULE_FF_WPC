"""FF-79: Job Type master (klasifikasi transaksi) dan account mapping
Product/Charge Code -> account.move.line, dengan fallback ke native product
income/expense account.

Desain (revisi setelah re-evaluasi): `job_type_id` adalah Many2one STORED
biasa yang bisa dipilih/diubah manual oleh user (Change Job Type), BUKAN
computed field. Classification (business_type/freight_type/sea_ship_mode)
hanya dipakai sebagai bantuan cari kandidat + filter domain + auto-fill saat
kandidatnya tepat satu -- TIDAK diasumsikan 1:1 dengan Job Type.

Scope: Air Export/Import, Sea FCL/LCL Export/Import saja (tidak Consol/
Domestic/Warehouse/Local Sales, sesuai tiket)."""
import inspect

from .common import FreightTestBase
from ..models.master_data import job_type as job_type_module
from ..models.common import job_type_resolver_mixin as resolver_mixin_module
from ..models.master_data.acct import charge_code_account_mapping as mapping_module


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


class TestFF79Propagation(FreightTestBase):
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
