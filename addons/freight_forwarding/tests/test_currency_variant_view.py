"""Test untuk FF-73 UAT fix (Bug 1): action_view_currency_variants() harus
selalu membuka form quotation sesuai freight_business_type (Sea ->
view_sea_quotation_form, Air -> view_air_quotation_form), terlepas dari
freight_business_type record yang diklik (root atau variant)."""
from .common import FreightTestBase


class TestCurrencyVariantFormView(FreightTestBase):

    def test_sea_currency_variants_use_sea_quotation_form(self):
        quotation = self._create_quotation()  # freight_business_type = sea
        expected_view_id = self.env.ref("freight_forwarding.view_sea_quotation_form").id

        action = quotation.action_view_currency_variants()

        form_views = [v for v in action["views"] if v[1] == "form"]
        self.assertEqual(len(form_views), 1)
        self.assertEqual(
            form_views[0][0], expected_view_id,
            msg="Currency Variants Sea harus membuka view_sea_quotation_form, "
                "bukan default sale.order form (yang tidak punya smart button Booking Sea)",
        )

    def test_air_currency_variants_use_air_quotation_form(self):
        quotation = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
        })
        expected_view_id = self.env.ref("freight_forwarding.view_air_quotation_form").id

        action = quotation.action_view_currency_variants()

        form_views = [v for v in action["views"] if v[1] == "form"]
        self.assertEqual(len(form_views), 1)
        self.assertEqual(form_views[0][0], expected_view_id)

    def test_sea_variant_opened_from_currency_variants_gets_same_form_as_quotation_list(self):
        """Manual UAT: record child Sea yang sama harus punya behavior UI
        sama baik dibuka dari smart button Currency Variants maupun dari Sea
        Quotation list -- keduanya harus resolve ke view_sea_quotation_form
        yang sama (yang membawa smart button Booking)."""
        root = self._create_quotation()
        variant_result = root.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        expected_view_id = self.env.ref("freight_forwarding.view_sea_quotation_form").id

        # Dibuka dari Currency Variants (baik dari root maupun dari variant)
        action_from_root = root.action_view_currency_variants()
        action_from_variant = variant.action_view_currency_variants()

        for action in (action_from_root, action_from_variant):
            form_views = [v for v in action["views"] if v[1] == "form"]
            self.assertEqual(form_views[0][0], expected_view_id)

    def test_sea_create_currency_variant_returns_sea_quotation_form(self):
        """FF-73 UAT fix (Bug 2): variant baru hilang smart button ketika
        langsung dibuka setelah action_create_currency_variant() karena action
        yang dikembalikan tidak menentukan form view sama sekali. Sekarang
        harus eksplisit pakai view_sea_quotation_form, sama seperti
        action_view_currency_variants()."""
        root = self._create_quotation()  # freight_business_type = sea
        expected_view_id = self.env.ref("freight_forwarding.view_sea_quotation_form").id

        action = root.action_create_currency_variant()

        self.assertEqual(action["views"], [(expected_view_id, "form")])

    def test_air_create_currency_variant_returns_air_quotation_form(self):
        root = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
        })
        expected_view_id = self.env.ref("freight_forwarding.view_air_quotation_form").id

        action = root.action_create_currency_variant()

        self.assertEqual(action["views"], [(expected_view_id, "form")])
