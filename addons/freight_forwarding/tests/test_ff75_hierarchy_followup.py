"""FF-75 independent-code-review follow-up: test coverage for the locked
domain decisions (Master/House hierarchy hardening, analytic invariant,
Air export commercial ownership, Master customer prefill removal, Sea
ship_mode/sea_ship_mode cleanup, Add to Master wizard hardening)."""
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger

from .common import FreightTestBase


class TestFF75HierarchyInvariants(FreightTestBase):
    def test_sea_house_without_master_raises(self):
        with self.assertRaises(ValidationError):
            self.env["freight.sea.job"].create({
                "record_level": "house",
                "freight_type": "export",
                "ship_mode": "fcl",
            })

    def test_air_house_without_master_raises(self):
        with self.assertRaises(ValidationError):
            self.env["freight.air.job"].create({
                "shipment_type": "house",
                "freight_type": "export",
            })

    def test_air_direct_without_master_is_valid(self):
        job = self.env["freight.air.job"].create({
            "shipment_type": "direct",
            "freight_type": "export",
        })
        self.assertTrue(job.exists())
        self.assertFalse(job.master_job_id)

    def test_sea_master_with_house_cannot_become_house(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        with self.assertRaises(ValidationError):
            master.write({"record_level": "house"})

    def test_air_master_with_house_cannot_become_house(self):
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        self.env["freight.air.job"].create({
            "shipment_type": "house", "master_job_id": master.id, "freight_type": "export",
        })
        with self.assertRaises(ValidationError):
            master.write({"shipment_type": "house"})

    def test_air_master_with_house_cannot_become_direct(self):
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        self.env["freight.air.job"].create({
            "shipment_type": "house", "master_job_id": master.id, "freight_type": "export",
        })
        with self.assertRaises(ValidationError):
            master.write({"shipment_type": "direct"})

    def test_sea_delete_master_with_house_rejected(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                master.unlink()

    def test_air_delete_master_with_house_rejected(self):
        master = self.env["freight.air.job"].create({"shipment_type": "master", "freight_type": "export"})
        self.env["freight.air.job"].create({
            "shipment_type": "house", "master_job_id": master.id, "freight_type": "export",
        })
        with mute_logger("odoo.sql_db"):
            with self.assertRaises(Exception):
                master.unlink()


class TestFF75AnalyticInvariant(FreightTestBase):
    def test_master_has_own_analytic(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "fcl",
        })
        self.assertTrue(master.analytic_account_id)

    def test_air_direct_has_own_analytic(self):
        job = self.env["freight.air.job"].create({"shipment_type": "direct", "freight_type": "export"})
        self.assertTrue(job.analytic_account_id)

    def test_house_uses_master_analytic(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        house = self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        self.assertEqual(house.analytic_account_id, master.analytic_account_id)

    def test_house_cannot_change_analytic_independently(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        house = self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        plan = self.env["account.analytic.plan"].search([], limit=1)
        rogue = self.env["account.analytic.account"].create({"name": "Rogue", "plan_id": plan.id})
        with self.assertRaises(ValidationError):
            house.write({"analytic_account_id": rogue.id})

    def test_master_analytic_change_cascades_to_house(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        house = self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        plan = self.env["account.analytic.plan"].search([], limit=1)
        new_analytic = self.env["account.analytic.account"].create({"name": "New Analytic", "plan_id": plan.id})
        master.write({"analytic_account_id": new_analytic.id})
        house.invalidate_recordset()
        self.assertEqual(house.analytic_account_id, new_analytic)


class TestFF75AirExportCommercialOwnership(FreightTestBase):
    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_master_is_not_commercial_owner_house_is(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        house = master.house_job_ids

        self.assertTrue(house)
        self.assertEqual(quotation.air_job_id, house,
            msg="Q1.air_job_id harus resolve ke House, bukan Master")
        self.assertNotEqual(quotation.air_job_id, master)
        self.assertFalse(master.sale_order_ids,
            msg="Master TIDAK boleh menerima sale_order_ids Booking untuk commercial ownership")
        self.assertEqual(house.source_quotation_id, quotation)

    def test_currency_variant_resolves_to_house_not_master(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        house = master.house_job_ids

        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])
        resolved = variant._get_commercial_group_jobsheets("freight.air.job")
        self.assertEqual(resolved, house)


class TestFF75MasterCustomerPrefill(FreightTestBase):
    def test_sea_export_master_customer_false(self):
        quotation = self._create_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])
        self.assertFalse(master.customer_id)

    def test_sea_house_customer_from_quotation(self):
        quotation = self._create_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])
        house = master.house_job_ids
        self.assertEqual(house.customer_id, quotation.partner_id)

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_air_export_master_partner_false(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        self.assertFalse(master.partner_id)

    def test_air_house_partner_from_quotation(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        house = master.house_job_ids
        self.assertEqual(house.partner_id, quotation.partner_id)


class TestFF75SeaShipMode(FreightTestBase):
    def test_quotation_uses_sea_ship_mode(self):
        quotation = self._create_quotation(sea_ship_mode="lcl")
        self.assertEqual(quotation.sea_ship_mode, "lcl")

    def test_quotation_to_booking_transfers_ship_mode(self):
        quotation = self._create_quotation(sea_ship_mode="lcl")
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])
        self.assertEqual(booking.ship_mode, "lcl")

    def test_booking_to_master_preserves_ship_mode(self):
        quotation = self._create_quotation(sea_ship_mode="lcl")
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])
        self.assertEqual(master.ship_mode, "lcl")

    def test_quotation_to_house_ship_mode_via_booking(self):
        quotation = self._create_quotation(sea_ship_mode="lcl")
        result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])
        house = master.house_job_ids
        self.assertEqual(house.ship_mode, "lcl")

    def test_import_master_and_house_get_ship_mode_from_quotation(self):
        quotation = self._create_quotation(freight_type="import", sea_ship_mode="fcl")
        result = quotation.action_convert_to_jobsheet_direct()
        master = self.env["freight.sea.job"].browse(result["res_id"])
        self.assertEqual(master.ship_mode, "fcl")
        house = master.house_job_ids
        self.assertEqual(house.ship_mode, "fcl")

    def test_fcl_master_max_one_house(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "fcl",
        })
        self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="fcl")
        with self.assertRaises(ValidationError):
            self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="fcl")

    def test_lcl_master_accepts_multiple_house(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="lcl")
        self.assertEqual(len(master.house_job_ids), 2)

    def test_no_requirement_house_ship_mode_equals_master(self):
        """Section F.6: House.ship_mode != Master.ship_mode HARUS tetap valid
        -- rule kesamaan itu belum diputuskan, jangan divalidasi."""
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "lcl",
        })
        house = self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="fcl")
        self.assertEqual(house.ship_mode, "fcl")
        self.assertEqual(master.ship_mode, "lcl")


class TestFF75AddToMasterWizardHardening(FreightTestBase):
    def _create_master(self, **kwargs):
        vals = {
            "record_level": "master",
            "freight_type": "export",
            "ship_mode": "lcl",
            "company_id": self.env.company.id,
        }
        vals.update(kwargs)
        return self.env["freight.sea.job"].create(vals)

    def _create_wizard(self, quotation, master):
        return self.env["freight.sea.add.to.master.wizard"].create({
            "quotation_id": quotation.id,
            "freight_type": quotation.freight_type,
            "company_id": quotation.company_id.id,
            "master_job_id": master.id,
        })

    def test_wizard_rejects_different_company(self):
        quotation = self._create_quotation()
        other_company = self.env["res.company"].create({"name": "FF75 Other Co"})
        master = self._create_master(company_id=other_company.id)
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()

    def test_wizard_rejects_different_freight_type(self):
        quotation = self._create_quotation(freight_type="export")
        master = self._create_master(freight_type="import")
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()

    def test_wizard_rejects_closed_master(self):
        quotation = self._create_quotation()
        master = self._create_master()
        master.action_close()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()

    def test_wizard_rejects_cancelled_master(self):
        quotation = self._create_quotation()
        master = self._create_master()
        master.action_cancel()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()

    def test_wizard_rejects_full_fcl_master(self):
        master = self._create_master(ship_mode="fcl")
        self._create_hbl(record_level="house", master_job_id=master.id, freight_type="export", ship_mode="fcl")
        quotation = self._create_quotation()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()


class TestFF75SourceQuotationResolverSemantic(FreightTestBase):
    """Audit semantic consistency _get_source_quotation(): Master (Sea &
    Air) bukan commercial owner Quotation manapun -- TIDAK boleh resolve
    lewat Booking. House selalu resolve dari field sendiri. Direct Air
    (out of scope) tetap boleh fallback ke Booking."""

    def test_sea_master_does_not_resolve_via_booking(self):
        quotation = self._create_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])

        self.assertEqual(booking.source_quotation_id, quotation)
        self.assertFalse(master._get_source_quotation())

    def test_sea_house_resolves_from_own_field(self):
        quotation = self._create_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.sea.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.sea.job"].browse(job_result["res_id"])
        house = master.house_job_ids

        self.assertEqual(house._get_source_quotation(), quotation)

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_air_master_does_not_resolve_via_booking(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])

        self.assertEqual(booking.source_quotation_id, quotation)
        self.assertFalse(master._get_source_quotation())

    def test_air_house_resolves_from_own_field(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])
        house = master.house_job_ids

        self.assertEqual(house._get_source_quotation(), quotation)

    def test_air_direct_still_falls_back_to_booking(self):
        """Direct out of scope -- behavior existing dipertahankan: kalau
        Direct dibuat lewat Booking tanpa source_quotation_id sendiri,
        resolusinya tetap lewat Booking._get_source_quotation()."""
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        booking.shipment_type = "direct"
        job_result = booking.action_create_job()
        direct = self.env["freight.air.job"].browse(job_result["res_id"])

        self.assertEqual(direct.shipment_type, "direct")
        self.assertFalse(direct.source_quotation_id,
            msg="Direct hasil Booking tidak menyimpan source_quotation_id sendiri")
        self.assertEqual(direct._get_source_quotation(), quotation,
            msg="Direct tetap boleh fallback ke Booking._get_source_quotation()")


class TestFF75ContainerTypeCleanup(FreightTestBase):
    def test_sea_models_no_longer_have_container_type_field(self):
        self.assertNotIn("container_type", self.env["freight.sea.job"]._fields)
        self.assertNotIn("container_type", self.env["freight.sea.booking"]._fields)
        self.assertNotIn("container_type", self.env["sale.order"]._fields)

    def test_container_type_id_still_works_on_cargo_info(self):
        master = self.env["freight.sea.job"].create({
            "record_level": "master", "freight_type": "export", "ship_mode": "fcl",
        })
        cargo = self.env["freight.sea.job.cargo.info"].create({
            "job_id": master.id,
            "container_type_id": self.container_type.id,
        })
        self.assertEqual(cargo.container_type_id, self.container_type)
