"""FF-81: Charge Table (product.pricelist header + product.pricelist.item
rules) & Cost Table (flat product.supplierinfo) extension -- defaulting,
Air/Sea isolation, editable override, and the Cargo column."""
from odoo.tests.common import TransactionCase


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
            'ff_type': 'sea',
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
        line = self._create_charge_line()
        self.assertEqual(line.ff_uom_id, self.uom_unit)
        self.assertEqual(line.ff_vat_id, self.tax_vat)
        self.assertEqual(line.ff_charge_unit, 'house')
        self.assertEqual(line.ff_description, 'Ocean Freight')

    def test_cost_table_defaults_from_product_on_create(self):
        line = self._create_cost_line(ff_type='air')
        self.assertEqual(line.ff_uom_id, self.uom_unit)
        self.assertEqual(line.ff_vat_id, self.tax_vat)
        self.assertEqual(line.ff_charge_unit, 'house')
        self.assertEqual(line.ff_description, 'Ocean Freight')

    def test_charge_table_explicit_override_not_overwritten_on_create(self):
        other_tax = self.env['account.tax'].create({
            'name': 'FF-81 Override VAT', 'amount': 5.0, 'type_tax_use': 'sale',
        })
        line = self._create_charge_line(ff_vat_id=other_tax.id, ff_charge_unit='volume')
        self.assertEqual(line.ff_vat_id, other_tax)
        self.assertEqual(line.ff_charge_unit, 'volume')
        # UoM was not overridden -> still defaults from the Charge Code.
        self.assertEqual(line.ff_uom_id, self.uom_unit)

    def test_charge_table_defaults_refreshed_on_product_change_via_write(self):
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
        line = self._create_charge_line()
        # Switching Item Code alone (no manual clearing of the old
        # defaults first) must refresh UoM/VAT/Charge Unit from the NEW
        # product.
        line.write({'product_tmpl_id': other_charge_code.id})
        self.assertEqual(line.ff_uom_id, other_uom)
        self.assertEqual(line.ff_charge_unit, 'pcs')
        self.assertFalse(line.ff_vat_id)
        self.assertEqual(line.ff_description, 'Handling Charge')

    def test_charge_table_explicit_override_not_overwritten_on_product_change_write(self):
        other_charge_code = self.env['product.template'].create({
            'name': 'Placeholder 3',
            'is_charge_code': True,
            'type': 'service',
            'cc_item_code': 'FF81-HC2',
            'cc_item_description': 'Handling Charge 2',
            'cc_uom_id': self.env.ref('uom.product_uom_dozen').id,
            'cc_charge_unit': 'pcs',
        })
        line = self._create_charge_line()
        # Product change + an explicit Charge Unit supplied in the SAME
        # write call -> Charge Unit override is preserved, UoM still
        # refreshes from the new product.
        line.write({'product_tmpl_id': other_charge_code.id, 'ff_charge_unit': 'weight'})
        self.assertEqual(line.ff_charge_unit, 'weight')
        self.assertEqual(line.ff_uom_id, self.env.ref('uom.product_uom_dozen'))

    # -- Air/Sea isolation ------------------------------------------------

    def test_charge_table_air_sea_isolation(self):
        # Charge Table isolation lives at the Pricelist (header) level.
        air_pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Air Pricelist', 'ff_type': 'air',
        })
        air_action = self.env.ref('freight_forwarding.action_freight_air_charge_table')
        sea_action = self.env.ref('freight_forwarding.action_freight_sea_charge_table')
        air_result = self.env['product.pricelist'].search(eval(air_action.domain))
        sea_result = self.env['product.pricelist'].search(eval(sea_action.domain))
        self.assertIn(air_pricelist, air_result)
        self.assertNotIn(self.pricelist, air_result)
        self.assertIn(self.pricelist, sea_result)
        self.assertNotIn(air_pricelist, sea_result)

    def test_cost_table_air_sea_isolation(self):
        # Cost Table isolation stays on the flat product.supplierinfo
        # record (not symmetrical with Charge Table).
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

    # -- Explicitly out of scope ------------------------------------------

    def test_cont_and_rate_charge_units_not_defined(self):
        # "Cont" and "Rate" are not part of the documented Charge Unit
        # selection (see FF-81 Out of Scope) -- confirm they remain absent.
        charge_unit_field = self.env['product.pricelist.item']._fields['ff_charge_unit']
        keys = dict(charge_unit_field.selection)
        self.assertNotIn('cont', keys)
        self.assertNotIn('rate', keys)

    # -- ff_cargo additive column on native list views ---------------------

    def test_ff_cargo_column_present_on_pricelist_item_rules_list(self):
        # Additive column on the native embedded Price Rules list -- must
        # not touch/rename any native field (min_quantity stays intact).
        view = self.env['product.pricelist'].get_view(
            view_id=self.env.ref('freight_forwarding.view_pricelist_form_inherit_freight').id,
            view_type='form',
        )
        self.assertIn('ff_cargo', view['arch'])
        self.assertIn('min_quantity', view['arch'])

    def test_ff_cargo_column_present_on_supplierinfo_list(self):
        view = self.env['product.supplierinfo'].get_view(
            view_id=self.env.ref('freight_forwarding.view_supplierinfo_list_inherit_freight').id,
            view_type='list',
        )
        self.assertIn('ff_cargo', view['arch'])
        self.assertIn('product_code', view['arch'])

    def test_ff_cargo_hidden_for_air_visible_for_sea_on_pricelist_rules_list(self):
        air_action = self.env.ref('freight_forwarding.action_freight_air_charge_table')
        sea_action = self.env.ref('freight_forwarding.action_freight_sea_charge_table')
        self.assertNotIn('ff_cargo_visible', air_action.context)
        self.assertIn("'ff_cargo_visible': True", sea_action.context)

    def test_ff_cargo_hidden_for_air_visible_for_sea_on_supplierinfo_list(self):
        air_action = self.env.ref('freight_forwarding.action_freight_air_cost_table')
        sea_action = self.env.ref('freight_forwarding.action_freight_sea_cost_table')
        self.assertNotIn('ff_cargo_visible', air_action.context)
        self.assertIn("'ff_cargo_visible': True", sea_action.context)
