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
