"""FF-80: native sale.order.user_id as the single source of truth for
Salesperson.

Decision (post-UAT revision): Booking and Jobsheet (Sea + Air) must NOT
carry a duplicate Salesperson field -- neither the old `salesman_id`
(hr.employee on Sea, res.users on Air) nor a custom `user_id`. There is no
propagation/copy of Salesperson from Quotation to Booking/Job. A downstream
consumer that needs Salesperson resolves it via
`source_quotation_id.user_id`, not a stored field. Master Job never has a
Salesperson (it can group Houses from different quotations).

`team_id` (Sales Team) stays independent and is never a Salesperson
fallback.
"""
from .common import FreightTestBase


class TestFF80QuotationSalesperson(FreightTestBase):
    """sale.order is the sole source of truth: native `user_id`, no custom
    `salesman_id`."""

    def test_sale_order_has_no_custom_salesman_id(self):
        self.assertNotIn(
            "salesman_id", self.env["sale.order"]._fields,
            msg="Custom quotation salesman_id harus sudah dihapus -- "
                "Salesperson memakai native user_id.",
        )

    def test_quotation_uses_native_user_id(self):
        quotation = self._create_quotation(user_id=self.env.user.id)
        self.assertEqual(quotation.user_id, self.env.user)


class TestFF80BookingJobHaveNoCustomSalesperson(FreightTestBase):
    """Sea/Air Booking and Job must not expose ANY custom Salesperson
    field -- neither the pre-FF-80 `salesman_id` nor the reverted FF-80
    `user_id` duplicate."""

    def test_sea_booking_has_no_custom_salesperson_field(self):
        fields_ = self.env["freight.sea.booking"]._fields
        self.assertNotIn("salesman_id", fields_)
        self.assertNotIn("user_id", fields_)

    def test_sea_job_has_no_custom_salesperson_field(self):
        fields_ = self.env["freight.sea.job"]._fields
        self.assertNotIn("salesman_id", fields_)
        self.assertNotIn("user_id", fields_)

    def test_air_booking_has_no_custom_salesperson_field(self):
        fields_ = self.env["freight.air.booking"]._fields
        self.assertNotIn("salesman_id", fields_)
        self.assertNotIn("user_id", fields_)

    def test_air_job_has_no_custom_salesperson_field(self):
        fields_ = self.env["freight.air.job"]._fields
        self.assertNotIn("salesman_id", fields_)
        self.assertNotIn("user_id", fields_)

    def test_sea_quotation_to_booking_to_job_flow_still_works(self):
        """Regression: removing the Salesperson duplicate must not break
        the underlying Quotation -> Booking -> Job conversion flow."""
        quotation = self._create_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])
        self.assertTrue(master.exists())
        self.assertEqual(master.record_level, "master")

    def test_air_quotation_to_booking_to_job_flow_still_works(self):
        quotation = self.env["sale.order"].create({
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        })
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        self.assertTrue(master.exists())
        self.assertEqual(master.shipment_type, "master")


class TestFF80SeaLegacyQuotationMigrationWizard(FreightTestBase):
    """freight.sea.quotation.migration.wizard (legacy freight_sea_quotation
    -> sale_order, active/executable code, NOT a historical migration) must
    resolve legacy salesman_id (hr.employee) to native sale_order.user_id
    via hr.employee.user_id -- and must NOT guess a Salesperson when the
    legacy employee has no linked user."""

    _LEGACY_TABLE_COLUMNS = """
        id integer PRIMARY KEY,
        freight_type varchar,
        quotation_title varchar,
        salesman_id integer,
        partner_id integer,
        service_level varchar,
        delivery_type_id integer,
        effective_date date,
        reference_number varchar,
        commodity_id integer,
        pickup_street varchar,
        pickup_street2 varchar,
        pickup_city integer,
        pickup_state_id integer,
        pickup_zip varchar,
        pickup_country_id integer,
        delivery_street varchar,
        delivery_street2 varchar,
        delivery_city integer,
        delivery_state_id integer,
        delivery_zip varchar,
        delivery_country_id integer,
        description_of_goods varchar,
        quantity integer,
        actual_weight numeric,
        volume numeric,
        chargeable_weight numeric,
        has_insurance boolean,
        insurance_id integer,
        loose_quantity integer,
        pcs integer,
        uom_id integer,
        length numeric,
        width numeric,
        height numeric,
        dimension numeric,
        origin_id integer,
        destination_id integer,
        est_transit_time_days integer,
        est_transit_time_note varchar,
        frequency varchar,
        frt_collect varchar,
        note text,
        header varchar,
        special_instruction text,
        footer varchar,
        original_quotation_id integer,
        port_of_loading_id integer,
        port_of_discharge_id integer,
        via_port_id integer,
        shipping_line_id integer,
        via2_id integer,
        via3_id integer
    """

    def _seed_legacy_quotation_table(self, rows):
        """rows: list of (sale_order_id, salesman_id). partner_id is always
        seeded from self.partner -- so.partner_id is NOT NULL and the wizard
        unconditionally overwrites it from fsq, unrelated to the
        Salesperson semantic under test here."""
        self.env.cr.execute(
            "CREATE TABLE freight_sea_quotation (%s)" % self._LEGACY_TABLE_COLUMNS
        )
        for so_id, salesman_id in rows:
            self.env.cr.execute(
                "INSERT INTO freight_sea_quotation (id, salesman_id, partner_id) "
                "VALUES (%s, %s, %s)",
                (so_id, salesman_id, self.partner.id),
            )

    def test_migration_wizard_writes_to_native_user_id(self):
        employee_with_user = self.env["hr.employee"].create({
            "name": "FF-80 Employee With User",
            "user_id": self.env.user.id,
        })
        employee_without_user = self.env["hr.employee"].create({
            "name": "FF-80 Employee Without User",
        })
        self.assertFalse(employee_without_user.user_id)

        # Case A: legacy salesman_id kosong -> so.user_id existing dipertahankan.
        quotation_a = self._create_quotation(user_id=self.env.user.id)
        # Case B: legacy salesman_id terisi, employee punya linked user -> ikuti user tsb.
        quotation_b = self._create_quotation(user_id=False)
        # Case C: legacy salesman_id terisi, employee TANPA linked user -> harus jadi kosong.
        quotation_c = self._create_quotation(user_id=self.env.user.id)

        self._seed_legacy_quotation_table([
            (quotation_a.id, None),
            (quotation_b.id, employee_with_user.id),
            (quotation_c.id, employee_without_user.id),
        ])

        self.env["freight.sea.quotation.migration.wizard"].create({}).action_migrate()
        self.env["sale.order"].invalidate_model()

        quotation_a, quotation_b, quotation_c = (
            self.env["sale.order"].browse([quotation_a.id, quotation_b.id, quotation_c.id])
        )
        self.assertEqual(
            quotation_a.user_id, self.env.user,
            msg="salesman_id legacy kosong -> so.user_id existing harus dipertahankan",
        )
        self.assertEqual(
            quotation_b.user_id, employee_with_user.user_id,
            msg="salesman_id legacy terisi & employee punya linked user -> harus ikut user tsb",
        )
        self.assertFalse(
            quotation_c.user_id,
            msg="salesman_id legacy terisi tapi employee TANPA linked user -> "
                "so.user_id harus kosong, bukan dipertahankan/ditebak",
        )


class TestFF80TeamIdUnaffected(FreightTestBase):
    """team_id (Sales Team) must remain a distinct concept from user_id
    (Salesperson) -- FF-80 explicitly forbids using it as a Salesperson
    fallback."""

    def test_team_id_and_user_id_are_independent_on_quotation(self):
        quotation = self._create_quotation(user_id=self.env.user.id)
        self.assertIn("team_id", self.env["sale.order"]._fields)
        field = self.env["sale.order"]._fields["team_id"]
        self.assertEqual(field.comodel_name, "crm.team")
        self.assertNotEqual(field.comodel_name, "res.users")
