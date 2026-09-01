"""Test untuk sinkronisasi akun analitik dan analytic distribution pada SO, PO, dan Vendor Bills dari Jobsheet (FF-60)."""
from .common import FreightTestBase


class TestAnalyticSync(FreightTestBase):
    """Verifikasi auto-populate analytic distribution pada PO, SO, dan Vendor Bills dari Jobsheet."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Master data: Product
        cls.product = cls.env["product.product"].create({
            "name": "Freight Forwarding Service",
            "type": "service",
            "list_price": 500000.0,
            "standard_price": 300000.0,
        })
        # Master data: Vendor
        cls.vendor = cls.env["res.partner"].create({
            "name": "Test Vendor Shipping",
            "is_company": True,
        })

    def test_po_line_auto_populates_analytic_distribution_from_jobsheet(self):
        """Saat menambahkan PO dengan sea_hbl_id, order_line otomatis terisi analytic_distribution 100%."""
        hbl = self._create_hbl()
        self.assertTrue(hbl.analytic_account_id, "HBL harus memiliki akun analitik")

        po = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "sea_hbl_id": hbl.id,
        })
        self.assertIn(po, hbl.purchase_order_ids, "PO harus otomatis tertaut ke purchase_order_ids pada HBL")

        line = self.env["purchase.order.line"].create({
            "order_id": po.id,
            "product_id": self.product.id,
            "product_qty": 1.0,
            "price_unit": 300000.0,
        })

        expected_distribution = {str(hbl.analytic_account_id.id): 100.0}
        self.assertEqual(
            line.analytic_distribution,
            expected_distribution,
            "analytic_distribution pada purchase.order.line harus terisi 100% akun analitik Jobsheet",
        )

    def test_so_line_auto_populates_analytic_distribution_from_jobsheet(self):
        """Saat menambahkan SO dengan sea_hbl_id, order_line otomatis terisi analytic_distribution 100%."""
        hbl = self._create_hbl()
        self.assertTrue(hbl.analytic_account_id, "HBL harus memiliki akun analitik")

        so = self._create_quotation(sea_hbl_id=hbl.id)
        self.assertIn(so, hbl.sale_order_ids, "SO harus otomatis tertaut ke sale_order_ids pada HBL")

        line = self.env["sale.order.line"].create({
            "order_id": so.id,
            "product_id": self.product.id,
            "product_uom_qty": 1.0,
            "price_unit": 500000.0,
        })

        expected_distribution = {str(hbl.analytic_account_id.id): 100.0}
        self.assertEqual(
            line.analytic_distribution,
            expected_distribution,
            "analytic_distribution pada sale.order.line harus terisi 100% akun analitik Jobsheet",
        )

    def test_vendor_bill_bridge_from_po(self):
        """_prepare_invoice dan _prepare_account_move_line pada PO menjamin sea_hbl_id dan analytic_distribution tersalurkan ke Vendor Bill."""
        hbl = self._create_hbl()
        po = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "sea_hbl_id": hbl.id,
        })
        po_line = self.env["purchase.order.line"].create({
            "order_id": po.id,
            "product_id": self.product.id,
            "product_qty": 1.0,
            "price_unit": 300000.0,
        })

        invoice_vals = po._prepare_invoice()
        self.assertEqual(
            invoice_vals.get("sea_hbl_id"),
            hbl.id,
            "Vendor Bill yang di-prepare dari PO harus membawa sea_hbl_id Jobsheet",
        )

        move_line_vals = po_line._prepare_account_move_line()
        expected_distribution = {str(hbl.analytic_account_id.id): 100.0}
        self.assertEqual(
            move_line_vals.get("analytic_distribution"),
            expected_distribution,
            "Baris Vendor Bill yang di-prepare dari PO line harus membawa analytic_distribution Jobsheet",
        )

    def test_sync_analytic_to_related_docs(self):
        """_sync_analytic_to_related_docs pada Jobsheet menyinkronkan analitik ke PO dan SO yang ditautkan belakangan."""
        hbl = self._create_hbl()
        expected_distribution = {str(hbl.analytic_account_id.id): 100.0}

        po = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
        })
        po_line = self.env["purchase.order.line"].create({
            "order_id": po.id,
            "product_id": self.product.id,
            "product_qty": 1.0,
            "price_unit": 300000.0,
        })
        # Reset distribution jika terisi
        po_line.analytic_distribution = False

        so = self._create_quotation()
        so_line = self.env["sale.order.line"].create({
            "order_id": so.id,
            "product_id": self.product.id,
            "product_uom_qty": 1.0,
            "price_unit": 500000.0,
        })
        so_line.analytic_distribution = False

        # Tautkan ke Jobsheet
        hbl.write({
            "purchase_order_ids": [(4, po.id)],
            "sale_order_ids": [(4, so.id)],
        })
        hbl._sync_analytic_to_related_docs()

        self.assertEqual(
            po_line.analytic_distribution,
            expected_distribution,
            "PO line harus tersinkronkan analytic_distribution-nya setelah dihubungkan ke Jobsheet",
        )
        self.assertEqual(
            so_line.analytic_distribution,
            expected_distribution,
            "SO line harus tersinkronkan analytic_distribution-nya setelah dihubungkan ke Jobsheet",
        )
        self.assertEqual(po.sea_hbl_id, hbl)
        self.assertEqual(so.sea_hbl_id, hbl)
