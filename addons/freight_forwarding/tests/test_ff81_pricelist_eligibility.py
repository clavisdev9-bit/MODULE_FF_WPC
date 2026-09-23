"""FF-81: Pricelist (Charge Table) eligibility for the Freight Quotation
"Freight Charge" header context (ff_type strict + wildcard-or-exact-match
on the other Charge Table header fields + validity date + Job Type via the
existing resolver)."""
from datetime import timedelta

from odoo.fields import Date

from .common import FreightTestBase


class TestFF81PricelistEligibility(FreightTestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.airport_origin = cls.env["freight.airport"].create({
            "code": "F8O", "name": "FF-81 Origin Airport",
            "country_id": cls.env.ref("base.id").id,
        })
        cls.airport_dest = cls.env["freight.airport"].create({
            "code": "F8D", "name": "FF-81 Destination Airport",
            "country_id": cls.env.ref("base.id").id,
        })
        cls.city_dest = cls.env["res.city"].create({
            "name": "FF-81 Destination City", "country_id": cls.env.ref("base.id").id,
        })
        cls.other_partner = cls.env["res.partner"].create({"name": "FF-81 Other Customer"})

    def _create_sea_pricelist(self, **kwargs):
        vals = {"name": "FF-81 Sea Charge Table", "ff_type": "sea"}
        vals.update(kwargs)
        return self.env["product.pricelist"].create(vals)

    def _create_air_pricelist(self, **kwargs):
        vals = {"name": "FF-81 Air Charge Table", "ff_type": "air"}
        vals.update(kwargs)
        return self.env["product.pricelist"].create(vals)

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    # -- ff_type strict isolation ------------------------------------------

    def test_sea_quotation_does_not_see_air_charge_table(self):
        sea_pricelist = self._create_sea_pricelist()
        air_pricelist = self._create_air_pricelist()
        quotation = self._create_quotation()
        self.assertIn(sea_pricelist, quotation.eligible_pricelist_ids)
        self.assertNotIn(air_pricelist, quotation.eligible_pricelist_ids)

    def test_air_quotation_does_not_see_sea_charge_table(self):
        sea_pricelist = self._create_sea_pricelist()
        air_pricelist = self._create_air_pricelist()
        quotation = self._create_air_quotation()
        self.assertIn(air_pricelist, quotation.eligible_pricelist_ids)
        self.assertNotIn(sea_pricelist, quotation.eligible_pricelist_ids)

    # -- Customer -------------------------------------------------------------

    def test_customer_exact_match_eligible(self):
        pricelist = self._create_sea_pricelist(ff_customer_id=self.partner.id)
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    def test_customer_mismatch_not_eligible(self):
        pricelist = self._create_sea_pricelist(ff_customer_id=self.other_partner.id)
        quotation = self._create_quotation()
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    def test_customer_blank_is_wildcard(self):
        pricelist = self._create_sea_pricelist()
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    # -- Sea route (POL/POD/Via) ----------------------------------------------

    def test_sea_route_exact_match_eligible(self):
        pricelist = self._create_sea_pricelist(
            ff_port_of_loading_id=self.port_loading.id,
            ff_port_of_discharge_id=self.port_discharge.id,
        )
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    def test_sea_route_mismatch_not_eligible(self):
        other_port = self.env["freight.port"].create({"code": "FF81P2", "name": "FF-81 Other Port"})
        pricelist = self._create_sea_pricelist(ff_port_of_loading_id=other_port.id)
        quotation = self._create_quotation()
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    def test_sea_route_blank_is_wildcard(self):
        pricelist = self._create_sea_pricelist()
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    # -- Air route (Airport Origin/Destination/Via) ---------------------------

    def test_air_route_exact_match_eligible(self):
        pricelist = self._create_air_pricelist(ff_airport_of_origin_id=self.airport_origin.id)
        quotation = self._create_air_quotation(airport_of_origin_id=self.airport_origin.id)
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    def test_air_route_mismatch_not_eligible(self):
        pricelist = self._create_air_pricelist(ff_airport_of_origin_id=self.airport_origin.id)
        quotation = self._create_air_quotation(airport_of_origin_id=self.airport_dest.id)
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    def test_air_route_blank_is_wildcard(self):
        pricelist = self._create_air_pricelist()
        quotation = self._create_air_quotation(airport_of_origin_id=self.airport_origin.id)
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    # -- Destination City ------------------------------------------------------

    def test_destination_exact_match_eligible(self):
        pricelist = self._create_sea_pricelist(ff_destination_city_id=self.city_dest.id)
        quotation = self._create_quotation(destination_id=self.city_dest.id)
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    def test_destination_mismatch_not_eligible(self):
        other_city = self.env["res.city"].create({
            "name": "FF-81 Other City", "country_id": self.env.ref("base.id").id,
        })
        pricelist = self._create_sea_pricelist(ff_destination_city_id=other_city.id)
        quotation = self._create_quotation(destination_id=self.city_dest.id)
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    def test_destination_blank_is_wildcard(self):
        pricelist = self._create_sea_pricelist()
        quotation = self._create_quotation(destination_id=self.city_dest.id)
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    # -- Validity date ----------------------------------------------------------

    def test_validity_date_within_range_eligible(self):
        today = Date.context_today(self.env.user)
        pricelist = self._create_sea_pricelist(
            ff_effective_date=today - timedelta(days=1),
            ff_expiry_date=today + timedelta(days=1),
        )
        quotation = self._create_quotation(valid_from=today)
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    def test_validity_date_expired_not_eligible(self):
        today = Date.context_today(self.env.user)
        pricelist = self._create_sea_pricelist(ff_expiry_date=today - timedelta(days=1))
        quotation = self._create_quotation(valid_from=today)
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    def test_validity_date_not_yet_effective_not_eligible(self):
        today = Date.context_today(self.env.user)
        pricelist = self._create_sea_pricelist(ff_effective_date=today + timedelta(days=1))
        quotation = self._create_quotation(valid_from=today)
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    # -- Inactive Pricelist ------------------------------------------------------

    def test_inactive_pricelist_not_eligible(self):
        pricelist = self._create_sea_pricelist()
        pricelist.active = False
        quotation = self._create_quotation()
        self.assertNotIn(pricelist, quotation.eligible_pricelist_ids)

    # -- TBD fields never affect eligibility --------------------------------

    def test_tbd_fields_do_not_affect_eligibility(self):
        pricelist = self._create_sea_pricelist(
            ff_valid_flag=False,
            ff_standard_charge_flag=False,
            ff_freight_collect=False,
            ff_transit_time=999,
            ff_frequency='irrelevant',
            ff_note='irrelevant',
            ff_note_code='irrelevant',
        )
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    # -- Job Type (via existing resolver, deterministic candidate only) -----

    def test_job_type_exact_match_eligible_when_resolved_unambiguous(self):
        job_type = self.env["freight.job.type"].create({
            "code": "FF81JTX", "name": "FF-81 Sea Export FCL",
            "business_type": "sea", "freight_type": "export", "sea_ship_mode": "fcl",
        })
        pricelist = self._create_sea_pricelist(ff_job_type_id=job_type.id)
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)

    def test_job_type_ambiguous_candidate_not_guessed(self):
        """FF-81: kalau klasifikasi transaksi (business_type/freight_type/
        sea_ship_mode) resolve ke LEBIH DARI SATU Job Type aktif, eligibility
        TIDAK menebak salah satu -- filtering Job Type di-skip untuk
        quotation ini, Charge Table dengan ff_job_type_id terisi tetap
        eligible (bukan otomatis dianggap tidak eligible)."""
        job_type_a = self.env["freight.job.type"].create({
            "code": "FF81JTA", "name": "FF-81 Sea Export FCL A",
            "business_type": "sea", "freight_type": "export", "sea_ship_mode": "fcl",
        })
        self.env["freight.job.type"].create({
            "code": "FF81JTB", "name": "FF-81 Sea Export FCL B",
            "business_type": "sea", "freight_type": "export", "sea_ship_mode": "fcl",
        })
        pricelist = self._create_sea_pricelist(ff_job_type_id=job_type_a.id)
        quotation = self._create_quotation()
        self.assertIn(pricelist, quotation.eligible_pricelist_ids)
