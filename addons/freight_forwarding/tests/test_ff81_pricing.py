"""FF-81: Charge Table (product.pricelist header + product.pricelist.item
rules) & Cost Table (flat product.supplierinfo) extension -- defaulting,
Air/Sea isolation, editable override, header fields, and header validity
precedence over native line date_start/date_end."""
from datetime import date, timedelta

from odoo.tests.common import TransactionCase


def _datetime_str(a_date):
    """Native date_start/date_end are Datetime; build a midnight timestamp
    string for a given date() without relying on any FF-81 code."""
    return f'{a_date.isoformat()} 00:00:00'


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

    def _create_charge_line(self, pricelist=None, **kwargs):
        vals = {
            'pricelist_id': (pricelist or self.pricelist).id,
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

    def test_cost_table_defaults_from_product_on_create(self):
        line = self._create_cost_line(ff_type='air')
        self.assertEqual(line.ff_uom_id, self.uom_unit)
        self.assertEqual(line.ff_vat_id, self.tax_vat)
        self.assertEqual(line.ff_charge_unit, 'house')

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

    def test_supplierinfo_cost_table_actions_flag_ff_type_visible(self):
        # Both Air and Sea Cost Table actions must mark ff_type_visible so
        # the additive FF columns use column_invisible scoped to this
        # context, and stay hidden on the native Vendor Pricelist list.
        air_action = self.env.ref('freight_forwarding.action_freight_air_cost_table')
        sea_action = self.env.ref('freight_forwarding.action_freight_sea_cost_table')
        self.assertIn("'ff_type_visible': True", air_action.context)
        self.assertIn("'ff_type_visible': True", sea_action.context)

    def test_ff_cargo_uses_column_invisible_on_pricelist_rules_list(self):
        # Row-level `invisible` on the embedded Price Rules list does not
        # hide the whole column -- it left the Cargo header visible (with
        # empty cells) on Air Charge Tables. Must use `column_invisible`
        # so the column fully disappears outside `ff_cargo_visible`
        # context (Air Charge Table, native Pricelist).
        view = self.env['product.pricelist'].get_view(
            view_id=self.env.ref('freight_forwarding.view_pricelist_form_inherit_freight').id,
            view_type='form',
        )
        arch = view['arch']
        self.assertIn(
            "name=\"ff_cargo\" optional=\"show\" width=\"70px\" "
            "column_invisible=\"not context.get('ff_cargo_visible')\"",
            arch,
        )

    def test_ff_columns_use_column_invisible_on_supplierinfo_list(self):
        # Row-level `invisible` does not hide a column from the native
        # list -- these must use `column_invisible` so the whole column
        # disappears when opened outside the FF Cost Table actions.
        view = self.env['product.supplierinfo'].get_view(
            view_id=self.env.ref('freight_forwarding.view_supplierinfo_list_inherit_freight').id,
            view_type='list',
        )
        arch = view['arch']
        for field_name in ('ff_uom_id', 'ff_vat_id', 'ff_charge_unit'):
            self.assertIn(f'name="{field_name}" optional="show" width=', arch)
            self.assertIn(
                f"column_invisible=\"not context.get('ff_type_visible')\"",
                arch,
            )
        self.assertIn('name="ff_cargo" optional="show" width=', arch)
        self.assertIn(
            "column_invisible=\"not context.get('ff_type_visible') or "
            "not context.get('ff_cargo_visible')\"",
            arch,
        )

    # -- ff_description removed (was only a duplicate display column) -----

    def test_ff_description_field_removed(self):
        self.assertNotIn('ff_description', self.env['product.pricelist.item']._fields)
        self.assertNotIn('ff_description', self.env['product.supplierinfo']._fields)

    # -- Charge Table Header: name/currency/company/active/valid untouched -

    def test_pricelist_name_is_the_only_mandatory_header_field(self):
        name_field = self.env['product.pricelist']._fields['name']
        self.assertTrue(name_field.required)
        for optional_field in (
            'ff_description', 'ff_job_type_id', 'ff_customer_id',
            'ff_destination_city_id', 'ff_valid_flag', 'ff_standard_charge_flag',
            'ff_effective_date', 'ff_expiry_date', 'ff_transit_time',
            'ff_frequency', 'ff_freight_collect', 'ff_note', 'ff_note_code',
        ):
            self.assertFalse(
                self.env['product.pricelist']._fields[optional_field].required,
                f'{optional_field} must be optional',
            )

    def test_customer_separate_from_company(self):
        customer = self.env['res.partner'].create({'name': 'FF-81 Customer'})
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Header Test', 'ff_type': 'sea', 'ff_customer_id': customer.id,
        })
        self.assertEqual(pricelist.ff_customer_id, customer)
        # native company_id (internal Odoo company) is untouched/independent
        # from ff_customer_id -- it must never resolve to the Customer.
        self.assertNotEqual(pricelist.company_id, customer)

    def test_valid_flag_does_not_affect_native_active(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Valid Flag Test', 'ff_type': 'sea', 'ff_valid_flag': False,
        })
        self.assertTrue(pricelist.active)
        pricelist.active = False
        self.assertFalse(pricelist.ff_valid_flag)

    def test_ff_flag_fields_are_boolean(self):
        for field_name in ('ff_valid_flag', 'ff_standard_charge_flag', 'ff_freight_collect'):
            self.assertEqual(
                self.env['product.pricelist']._fields[field_name].type, 'boolean',
                f'{field_name} must be a Boolean field',
            )

    def test_ff_note_is_text_note_code_is_char(self):
        self.assertEqual(self.env['product.pricelist']._fields['ff_note'].type, 'text')
        self.assertEqual(self.env['product.pricelist']._fields['ff_note_code'].type, 'char')

    def test_header_validity_uses_daterange_widget(self):
        view = self.env['product.pricelist'].get_view(
            view_id=self.env.ref('freight_forwarding.view_pricelist_form_inherit_freight').id,
            view_type='form',
        )
        arch = view['arch']
        self.assertIn('widget="daterange"', arch)
        self.assertIn("'end_date_field': 'ff_expiry_date'", arch)
        self.assertIn('string="Validity Period"', arch)

    def test_job_type_module_related_readonly(self):
        job_type = self.env['freight.job.type'].create({
            'code': 'FF81JT', 'name': 'FF-81 Job Type', 'module_code': 'SEA-EXP',
        })
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Job Type Test', 'ff_type': 'sea', 'ff_job_type_id': job_type.id,
        })
        self.assertEqual(pricelist.ff_module_code, 'SEA-EXP')
        self.assertTrue(self.env['product.pricelist']._fields['ff_module_code'].readonly)

    def test_destination_uses_res_city_and_is_common(self):
        city = self.env['res.city'].create({
            'name': 'FF-81 City', 'country_id': self.env.ref('base.id').id,
        })
        air_pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Air Destination Test', 'ff_type': 'air',
            'ff_destination_city_id': city.id,
        })
        sea_pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Sea Destination Test', 'ff_type': 'sea',
            'ff_destination_city_id': city.id,
        })
        self.assertEqual(air_pricelist.ff_destination_city_id, city)
        self.assertEqual(sea_pricelist.ff_destination_city_id, city)

    def test_sea_route_fields_use_freight_port(self):
        port = self.env['freight.port'].create({'code': 'FF81P', 'name': 'FF-81 Port'})
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Sea Route Test', 'ff_type': 'sea',
            'ff_port_of_loading_id': port.id,
            'ff_port_of_discharge_id': port.id,
            'ff_via_port_id': port.id,
        })
        self.assertEqual(pricelist.ff_port_of_loading_id, port)
        self.assertEqual(pricelist.ff_port_of_discharge_id, port)
        self.assertEqual(pricelist.ff_via_port_id, port)

    def test_air_route_fields_use_airport_master(self):
        airport = self.env['freight.airport'].create({
            'code': 'FFP', 'name': 'FF-81 Airport', 'country_id': self.env.ref('base.id').id,
        })
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Air Route Test', 'ff_type': 'air',
            'ff_airport_of_origin_id': airport.id,
            'ff_airport_of_destination_id': airport.id,
            'ff_via_airport_id': airport.id,
        })
        self.assertEqual(pricelist.ff_airport_of_origin_id, airport)
        self.assertEqual(pricelist.ff_airport_of_destination_id, airport)
        self.assertEqual(pricelist.ff_via_airport_id, airport)

    def test_sea_route_fields_hidden_on_air_view_and_vice_versa(self):
        view = self.env['product.pricelist'].get_view(
            view_id=self.env.ref('freight_forwarding.view_pricelist_form_inherit_freight').id,
            view_type='form',
        )
        arch = view['arch']
        self.assertIn('ff_port_of_loading_id', arch)
        self.assertIn('ff_airport_of_origin_id', arch)
        self.assertIn("ff_type != 'sea'", arch)
        self.assertIn("ff_type != 'air'", arch)

    def test_storage_only_fields_do_not_affect_pricing(self):
        # Valid Flag / Standard Charge Flag / Freight Collect / Transit Time
        # / Frequency / Note / Note Code must have zero effect on the price
        # actually computed for a rule -- only `fixed_price` matters here.
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Storage Only Test', 'ff_type': 'sea',
            'ff_valid_flag': False,
            'ff_standard_charge_flag': False,
            'ff_freight_collect': False,
            'ff_transit_time': 999,
            'ff_frequency': 'irrelevant',
            'ff_note': 'irrelevant',
            'ff_note_code': 'irrelevant',
        })
        self._create_charge_line(pricelist=pricelist, fixed_price=77.0)
        product = self.charge_code.product_variant_id
        price, rule = pricelist._get_product_price_rule(product, 1.0)
        self.assertEqual(price, 77.0)

    # -- Header validity precedence over native line date_start/date_end ---

    def test_header_effective_date_overrides_line_date_start(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Header Validity Test', 'ff_type': 'sea',
            'ff_effective_date': date.today() - timedelta(days=1),
        })
        # Line's own native date_start is in the FUTURE (would normally make
        # it inapplicable today) -- header Effective Date must override it.
        self._create_charge_line(
            pricelist=pricelist,
            date_start=_datetime_str(date.today() + timedelta(days=30)),
        )
        product = self.charge_code.product_variant_id
        price, rule = pricelist._get_product_price_rule(product, 1.0)
        self.assertEqual(price, 100.0)
        self.assertTrue(rule)

    def test_header_effective_date_in_future_blocks_all_lines(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Future Header Test', 'ff_type': 'sea',
            'ff_effective_date': date.today() + timedelta(days=30),
        })
        self._create_charge_line(pricelist=pricelist)
        product = self.charge_code.product_variant_id
        price, rule = pricelist._get_product_price_rule(product, 1.0)
        self.assertFalse(rule)

    def test_header_expiry_date_empty_falls_back_to_line_date_end(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 No Header Expiry Test', 'ff_type': 'sea',
            'ff_effective_date': date.today() - timedelta(days=1),
            # ff_expiry_date left empty -> native line date_end still applies.
        })
        self._create_charge_line(
            pricelist=pricelist,
            date_end=_datetime_str(date.today() - timedelta(days=1)),
        )
        product = self.charge_code.product_variant_id
        price, rule = pricelist._get_product_price_rule(product, 1.0)
        self.assertFalse(rule)

    def test_header_expiry_date_valid_overrides_line_date_end(self):
        # Line's own native date_end already passed (would normally make it
        # inapplicable today) -- header Expiry Date, still in the future,
        # must override it and keep the rule applicable.
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Header Expiry Override Test', 'ff_type': 'sea',
            'ff_expiry_date': date.today() + timedelta(days=30),
        })
        self._create_charge_line(
            pricelist=pricelist,
            date_end=_datetime_str(date.today() - timedelta(days=1)),
        )
        product = self.charge_code.product_variant_id
        price, rule = pricelist._get_product_price_rule(product, 1.0)
        self.assertEqual(price, 100.0)
        self.assertTrue(rule)

    def test_header_expiry_date_expired_blocks_all_lines(self):
        # Header Expiry Date already passed -> the whole Charge Table is
        # expired, even though the line's own native date_end has not been
        # reached yet.
        pricelist = self.env['product.pricelist'].create({
            'name': 'FF-81 Header Expiry Expired Test', 'ff_type': 'sea',
            'ff_expiry_date': date.today() - timedelta(days=1),
        })
        self._create_charge_line(
            pricelist=pricelist,
            date_end=_datetime_str(date.today() + timedelta(days=30)),
        )
        product = self.charge_code.product_variant_id
        price, rule = pricelist._get_product_price_rule(product, 1.0)
        self.assertFalse(rule)

    def test_no_header_dates_keeps_native_line_date_behavior(self):
        # No header boundary set at all -> pure native behaviour, unaffected
        # by the FF-81 override.
        self._create_charge_line(
            date_start=_datetime_str(date.today() + timedelta(days=30)),
        )
        product = self.charge_code.product_variant_id
        price, rule = self.pricelist._get_product_price_rule(product, 1.0)
        self.assertFalse(rule)
