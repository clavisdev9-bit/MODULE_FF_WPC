"""FF-81: Charge Table (product.pricelist.item) & Cost Table
(product.supplierinfo) extension -- defaulting, Air/Sea isolation,
editable override, and the documented Quantity Calculation formulas."""
from odoo.tests.common import TransactionCase

from odoo.addons.freight_forwarding.models.master_data.acct.charge_code import (
    compute_charge_quantity,
)


class TestFF81Pricing(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.tax_vat = cls.env['account.tax'].create({
            'name': 'FF-81 Test VAT',
            'amount': 11.0,
            'type_tax_use': 'sale',
        })
        cls.charge_code = cls.env['product.template'].create({
            'name': 'Placeholder',
            'is_charge_code': True,
            'type': 'service',
            'cc_item_code': 'FF81-OF',
            'cc_item_description': 'Ocean Freight',
            'cc_uom_id': cls.uom_unit.id,
            'cc_vat_id': cls.tax_vat.id,
            'cc_charge_unit': 'house',
        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'FF-81 Test Pricelist',
        })
        cls.vendor = cls.env['res.partner'].create({'name': 'FF-81 Test Vendor'})

    def _create_charge_line(self, **kwargs):
        vals = {
            'pricelist_id': self.pricelist.id,
            'product_tmpl_id': self.charge_code.id,
            'applied_on': '1_product',
            'compute_price': 'fixed',
            'fixed_price': 100.0,
        }
        vals.update(kwargs)
        return self.env['product.pricelist.item'].create(vals)

    def _create_cost_line(self, **kwargs):
        vals = {
            'partner_id': self.vendor.id,
            'product_tmpl_id': self.charge_code.id,
            'price': 50.0,
        }
        vals.update(kwargs)
        return self.env['product.supplierinfo'].create(vals)

    # -- Defaulting (server-side create, not just onchange) -------------

    def test_charge_table_defaults_from_product_on_create(self):
        line = self._create_charge_line(ff_type='sea')
        self.assertEqual(line.ff_uom_id, self.uom_unit)
        self.assertEqual(line.ff_vat_id, self.tax_vat)
        self.assertEqual(line.ff_charge_unit, 'house')
        self.assertEqual(line.ff_description, 'FF81-OF - Ocean Freight')

    def test_cost_table_defaults_from_product_on_create(self):
        line = self._create_cost_line(ff_type='air')
        self.assertEqual(line.ff_uom_id, self.uom_unit)
        self.assertEqual(line.ff_vat_id, self.tax_vat)
        self.assertEqual(line.ff_charge_unit, 'house')

    def test_charge_table_explicit_override_not_overwritten_on_create(self):
        other_tax = self.env['account.tax'].create({
            'name': 'FF-81 Override VAT', 'amount': 5.0, 'type_tax_use': 'sale',
        })
        line = self._create_charge_line(
            ff_type='sea', ff_vat_id=other_tax.id, ff_charge_unit='volume',
        )
        self.assertEqual(line.ff_vat_id, other_tax)
        self.assertEqual(line.ff_charge_unit, 'volume')
        # UoM was not overridden -> still defaults from the Charge Code.
        self.assertEqual(line.ff_uom_id, self.uom_unit)

    def test_charge_table_defaults_reapplied_on_product_change_via_write(self):
        other_uom = self.env.ref('uom.product_uom_dozen')
        other_charge_code = self.env['product.template'].create({
            'name': 'Placeholder 2',
            'is_charge_code': True,
            'type': 'service',
            'cc_item_code': 'FF81-HC',
            'cc_item_description': 'Handling Charge',
            'cc_uom_id': other_uom.id,
            'cc_charge_unit': 'pcs',
        })
        line = self._create_charge_line(ff_type='sea')
        line.write({'product_tmpl_id': other_charge_code.id, 'ff_charge_unit': False, 'ff_uom_id': False})
        self.assertEqual(line.ff_uom_id, other_uom)
        self.assertEqual(line.ff_charge_unit, 'pcs')
        self.assertEqual(line.ff_description, 'FF81-HC - Handling Charge')

    # -- Air/Sea isolation via ff_type ----------------------------------

    def test_charge_table_air_sea_isolation(self):
        air_line = self._create_charge_line(ff_type='air')
        sea_line = self._create_charge_line(ff_type='sea')
        air_action = self.env.ref('freight_forwarding.action_freight_air_charge_table')
        sea_action = self.env.ref('freight_forwarding.action_freight_sea_charge_table')
        air_domain = eval(air_action.domain)
        sea_domain = eval(sea_action.domain)
        air_result = self.env['product.pricelist.item'].search(air_domain)
        sea_result = self.env['product.pricelist.item'].search(sea_domain)
        self.assertIn(air_line, air_result)
        self.assertNotIn(sea_line, air_result)
        self.assertIn(sea_line, sea_result)
        self.assertNotIn(air_line, sea_result)

    def test_cost_table_air_sea_isolation(self):
        air_line = self._create_cost_line(ff_type='air')
        sea_line = self._create_cost_line(ff_type='sea')
        air_action = self.env.ref('freight_forwarding.action_freight_air_cost_table')
        sea_action = self.env.ref('freight_forwarding.action_freight_sea_cost_table')
        air_result = self.env['product.supplierinfo'].search(eval(air_action.domain))
        sea_result = self.env['product.supplierinfo'].search(eval(sea_action.domain))
        self.assertIn(air_line, air_result)
        self.assertNotIn(sea_line, air_result)
        self.assertIn(sea_line, sea_result)
        self.assertNotIn(air_line, sea_result)

    # -- Quantity Calculation (documented formulas only) -----------------

    def test_quantity_calculation_documented_formulas(self):
        self.assertEqual(compute_charge_quantity('20ft', container_count=3), 3)
        self.assertEqual(compute_charge_quantity('40ft', container_count=2), 2)
        self.assertEqual(compute_charge_quantity('45ft', container_count=1), 1)
        self.assertEqual(compute_charge_quantity('total_container', container_count=5), 5)
        self.assertEqual(compute_charge_quantity('rev_ton_cw', cm3=12000, kgs=1.5), 2.0)
        self.assertEqual(compute_charge_quantity('rev_ton_cw', cm3=3000, kgs=10), 10)
        self.assertEqual(compute_charge_quantity('shipment'), 1)
        self.assertEqual(compute_charge_quantity('house', house_count=4), 4)
        self.assertEqual(compute_charge_quantity('volume', volume=7.5), 7.5)
        self.assertEqual(compute_charge_quantity('weight', weight=120.0), 120.0)
        self.assertEqual(compute_charge_quantity('pcs', pcs=8), 8)

    def test_quantity_calculation_undocumented_unit_returns_none(self):
        # rev_ton_rnd, subhouse_bl, ccfee, block_4m3, block_3m3,
        # invoice_charge_weight have no confirmed formula in FF-81 -- must
        # not be guessed.
        for unit in ('rev_ton_rnd', 'subhouse_bl', 'ccfee', 'block_4m3',
                     'block_3m3', 'invoice_charge_weight'):
            self.assertIsNone(compute_charge_quantity(unit, container_count=1, kgs=1, cm3=1))
