"""FF-80: Standarize Salesperson field across the Freight flow.

Canonical: `user_id -> res.users` end-to-end. `sale.order` uses the native
Odoo `user_id` (custom quotation `salesman_id` removed). Sea/Air
Booking/Jobsheet expose their own `user_id -> res.users` (renamed from the
old `salesman_id`, which was `hr.employee` on Sea and `res.users` on Air).

These tests cover propagation for both Quotation -> Booking -> Jobsheet and
the direct Quotation -> Jobsheet (Import) flow, for Sea and Air.
"""
from .common import FreightTestBase


class TestFF80QuotationSalesperson(FreightTestBase):
    """sale.order no longer exposes the custom `salesman_id` field."""

    def test_sale_order_has_no_custom_salesman_id(self):
        self.assertNotIn(
            "salesman_id", self.env["sale.order"]._fields,
            msg="Custom quotation salesman_id harus sudah dihapus -- "
                "Salesperson memakai native user_id.",
        )

    def test_quotation_uses_native_user_id(self):
        quotation = self._create_quotation(user_id=self.env.user.id)
        self.assertEqual(quotation.user_id, self.env.user)


class TestFF80SeaBookingJobsheetSalesperson(FreightTestBase):
    """Sea Booking/Job expose user_id (res.users), not the old hr.employee
    salesman_id."""

    def test_sea_booking_has_no_legacy_salesman_id(self):
        self.assertNotIn("salesman_id", self.env["freight.sea.booking"]._fields)
        self.assertIn("user_id", self.env["freight.sea.booking"]._fields)
        field = self.env["freight.sea.booking"]._fields["user_id"]
        self.assertEqual(field.comodel_name, "res.users")

    def test_sea_job_has_no_legacy_salesman_id(self):
        self.assertNotIn("salesman_id", self.env["freight.sea.job"]._fields)
        self.assertIn("user_id", self.env["freight.sea.job"]._fields)
        field = self.env["freight.sea.job"]._fields["user_id"]
        self.assertEqual(field.comodel_name, "res.users")

    def test_quotation_to_booking_carries_user_id(self):
        quotation = self._create_quotation(user_id=self.env.user.id)
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])
        self.assertEqual(booking.user_id, self.env.user)

    def test_booking_to_job_carries_user_id(self):
        """Booking -> Create Job (action_create_job) membawa user_id Booking
        ke Master Job."""
        booking = self._create_booking(user_id=self.env.user.id)
        result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        self.assertEqual(master.user_id, self.env.user)

    def test_direct_quotation_to_job_carries_user_id(self):
        """Import quotation -> Create Job (tanpa Booking) tetap membawa
        user_id ke House pertama."""
        quotation = self._create_quotation(freight_type="import", user_id=self.env.user.id)
        result = quotation.action_convert_to_jobsheet_direct()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        house = master.house_job_ids
        self.assertTrue(house)
        self.assertEqual(house.user_id, self.env.user)


class TestFF80AirBookingJobsheetSalesperson(FreightTestBase):
    """Air Booking/Job: legacy salesman_id (res.users) renamed to user_id."""

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_air_booking_has_no_legacy_salesman_id(self):
        self.assertNotIn("salesman_id", self.env["freight.air.booking"]._fields)
        self.assertIn("user_id", self.env["freight.air.booking"]._fields)
        field = self.env["freight.air.booking"]._fields["user_id"]
        self.assertEqual(field.comodel_name, "res.users")

    def test_air_job_has_no_legacy_salesman_id(self):
        self.assertNotIn("salesman_id", self.env["freight.air.job"]._fields)
        self.assertIn("user_id", self.env["freight.air.job"]._fields)
        field = self.env["freight.air.job"]._fields["user_id"]
        self.assertEqual(field.comodel_name, "res.users")

    def test_air_quotation_to_booking_carries_user_id(self):
        quotation = self._create_air_quotation(user_id=self.env.user.id)
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(result["res_id"])
        self.assertEqual(booking.user_id, self.env.user)

    def test_air_booking_to_job_carries_user_id(self):
        quotation = self._create_air_quotation(user_id=self.env.user.id)
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])

        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        self.assertEqual(master.user_id, self.env.user)

    def test_direct_air_quotation_to_job_carries_user_id(self):
        """Import Air quotation -> Create Job (tanpa Booking) membawa
        user_id ke House pertama."""
        quotation = self._create_air_quotation(freight_type="import", user_id=self.env.user.id)
        result = quotation.action_convert_to_jobsheet_direct()
        master = self.env["freight.air.job"].browse(result["res_id"])
        house = master.house_job_ids
        self.assertTrue(house)
        self.assertEqual(house.user_id, self.env.user)

    def test_air_quotation_to_booking_no_fallback_to_current_user(self):
        """FF-80 UAT fix: kalau quotation.user_id kosong, Booking.user_id
        HARUS ikut kosong -- bukan diam-diam fallback ke self.env.uid
        (user yang menjalankan action)."""
        quotation = self._create_air_quotation(user_id=False)
        self.assertFalse(quotation.user_id)
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(result["res_id"])
        self.assertFalse(
            booking.user_id,
            msg="Booking.user_id tidak boleh fallback ke env.uid saat source kosong",
        )

    def test_direct_air_quotation_to_job_no_fallback_to_current_user(self):
        """FF-80 UAT fix: direct Quotation -> Job (Import) juga tidak boleh
        fallback ke env.uid kalau quotation.user_id kosong."""
        quotation = self._create_air_quotation(freight_type="import", user_id=False)
        result = quotation.action_convert_to_jobsheet_direct()
        master = self.env["freight.air.job"].browse(result["res_id"])
        house = master.house_job_ids
        self.assertTrue(house)
        self.assertFalse(
            house.user_id,
            msg="House.user_id tidak boleh fallback ke env.uid saat source kosong",
        )


class TestFF80SeaLegacyQuotationMigrationWizard(FreightTestBase):
    """FF-80 UAT fix: freight.sea.quotation.migration.wizard (legacy
    freight_sea_quotation -> sale_order, active/executable code, NOT a
    historical migration) must resolve Salesperson the same way as the
    rest of FF-80 -- and must NOT preserve/guess a Salesperson when the
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

    def test_migration_wizard_salesperson_semantic(self):
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
