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

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_wizard_rejects_import_quotation_direct_call(self):
        """Section 1/2: proteksi bukan cuma UI/action_open -- direct-call ke
        action_add_to_master() dengan Quotation Import harus tetap ditolak."""
        quotation = self._create_quotation(freight_type="import")
        master = self._create_master()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()

    def test_wizard_rejects_air_quotation_on_sea_wizard(self):
        quotation = self._create_air_quotation()
        master = self._create_master()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()


class TestFF75AirAddToMasterQuotationGuard(FreightTestBase):
    """Section 2: freight.air.add.to.master.wizard harus menolak Quotation
    yang bukan Freight/bukan Air/bukan Export, langsung lewat backend
    action_add_to_master() -- bukan cuma UI/action_open/domain."""

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def _create_air_master(self, **kwargs):
        vals = {
            "shipment_type": "master",
            "freight_type": "export",
            "company_id": self.env.company.id,
        }
        vals.update(kwargs)
        return self.env["freight.air.job"].create(vals)

    def _create_wizard(self, quotation, master):
        return self.env["freight.air.add.to.master.wizard"].create({
            "quotation_id": quotation.id,
            "freight_type": quotation.freight_type,
            "company_id": quotation.company_id.id,
            "master_job_id": master.id,
        })

    def test_wizard_rejects_import_quotation_direct_call(self):
        quotation = self._create_air_quotation(freight_type="import")
        master = self._create_air_master()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()

    def test_wizard_rejects_sea_quotation_on_air_wizard(self):
        quotation = self._create_quotation()
        master = self._create_air_master()
        wizard = self._create_wizard(quotation, master)
        with self.assertRaises(UserError):
            wizard.action_add_to_master()


class TestFF75AddToMasterActionCollisionFix(FreightTestBase):
    """Manual UAT follow-up Section 1: SeaQuotation dan AirQuotation
    sama-sama _inherit="sale.order" dan sebelumnya sama-sama memakai nama
    method generik `action_open_add_to_master_wizard` -- yang belakangan
    dimuat MENANG untuk SEMUA quotation (Sea maupun Air), jadi tombol Sea
    bisa membuka wizard Air. Regression test ini memastikan masing-masing
    action sekarang membuka wizard model-nya sendiri."""

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_sea_quotation_action_opens_sea_wizard(self):
        quotation = self._create_quotation()
        action = quotation.action_open_sea_add_to_master_wizard()
        self.assertEqual(action["res_model"], "freight.sea.add.to.master.wizard")

    def test_air_quotation_action_opens_air_wizard(self):
        quotation = self._create_air_quotation()
        action = quotation.action_open_air_add_to_master_wizard()
        self.assertEqual(action["res_model"], "freight.air.add.to.master.wizard")


class TestFF75AirBookingCreateJobAlwaysMasterHouse(FreightTestBase):
    """Manual UAT follow-up Section 2: Direct AWB TIDAK dibuat lewat
    Booking -- Direct AWB dibuat langsung sebagai freight.air.job berdiri
    sendiri lewat flow/menu Direct AWB (AirQuotation._action_convert_to_jobsheet_direct_air),
    di luar Booking sama sekali. Karena itu Air Booking -> Create Job
    SELALU berarti Booking -> Master -> House, branching
    `is_direct = shipment_type == 'direct'` yang sebelumnya ada di
    action_create_job() dihapus total."""

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def test_first_call_creates_master_and_house(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])

        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])

        self.assertEqual(master.shipment_type, "master")
        self.assertEqual(len(master.house_job_ids), 1)
        self.assertEqual(master.house_job_ids.shipment_type, "house")
        self.assertEqual(master.house_job_ids.master_job_id, master)

    def test_second_call_is_idempotent_no_duplicate_master_or_house(self):
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])

        first_result = booking.action_create_job()
        second_result = booking.action_create_job()

        self.assertEqual(first_result["res_id"], second_result["res_id"],
            msg="Panggilan kedua harus membuka Master yang sama, bukan membuat Master baru")
        master = self.env["freight.air.job"].browse(second_result["res_id"])
        self.assertEqual(len(master.house_job_ids), 1,
            msg="Panggilan kedua tidak boleh menduplikasi House")

    def test_create_job_ignores_booking_shipment_type_direct(self):
        """Meskipun shipment_type Booking (field mixin, sekarang disembunyikan
        dari form) diset 'direct' secara langsung lewat backend, Create Job
        HARUS tetap menghasilkan Master + House, bukan Job standalone."""
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])
        booking.shipment_type = "direct"

        job_result = booking.action_create_job()
        master = self.env["freight.air.job"].browse(job_result["res_id"])

        self.assertEqual(master.shipment_type, "master")
        self.assertEqual(len(master.house_job_ids), 1)

    def test_direct_awb_standalone_menu_flow_unaffected(self):
        """Direct AWB (menu/flow standalone freight.air.job dengan
        default_shipment_type='direct', lihat views/air/hawb/hawb.xml) TIDAK
        pernah lewat Booking sama sekali dan TIDAK disentuh oleh perubahan
        Section 2 -- tetap bisa dibuat berdiri sendiri tanpa Master."""
        direct = self.env["freight.air.job"].create({
            "shipment_type": "direct",
            "freight_type": "export",
        })
        self.assertTrue(direct.exists())
        self.assertFalse(direct.master_job_id)


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
        """Manual UAT follow-up Section 2: Direct AWB TIDAK LAGI dibuat lewat
        Booking (booking.action_create_job() sekarang SELALU menghasilkan
        Master + House, terlepas dari booking.shipment_type). Fallback
        `_get_source_quotation()` lewat booking_id untuk shipment_type ==
        'direct' di freight.air.job dipertahankan di level kode (Direct
        standalone yang dibuat lewat menu Direct AWB tetap bisa punya
        booking_id manual), tapi jalur lama "Booking -> Direct" sudah tidak
        ada lagi -- test ini diupdate untuk memverifikasi fallback tersebut
        langsung lewat construction manual, bukan lewat
        booking.action_create_job()."""
        quotation = self._create_air_quotation()
        booking_result = quotation.action_convert_to_booking_direct()
        booking = self.env["freight.air.booking"].browse(booking_result["res_id"])

        direct = self.env["freight.air.job"].create({
            "shipment_type": "direct",
            "freight_type": "export",
            "booking_id": booking.id,
        })

        self.assertFalse(direct.source_quotation_id,
            msg="Direct tanpa source_quotation_id sendiri")
        self.assertEqual(direct._get_source_quotation(), quotation,
            msg="Direct tetap boleh fallback ke Booking._get_source_quotation() "
                "kalau booking_id di-set manual (behavior existing dipertahankan)")


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


class TestFF75SeaJobCustomerNoTagDomain(FreightTestBase):
    """Manual UAT follow-up Section 3: freight.sea.job.customer_id sebelumnya
    punya domain="[('category_id.name', '=', 'Customer')]" yang memblokir
    partner tanpa tag 'Customer' di UI. Domain dihapus total -- field
    sekarang plain Many2one tanpa domain sama sekali. Scope tidak melebar
    ke field partner-role lain (shipper/consignee/notify/delivery
    agent/warehouse/agent) -- domain field-field tersebut diaudit
    terpisah, belum bagian dari task ini."""

    def test_customer_id_field_has_no_domain(self):
        field = self.env["freight.sea.job"]._fields["customer_id"]
        self.assertFalse(field.domain,
            msg="customer_id tidak boleh lagi punya domain category_id.name == 'Customer'")

    def test_customer_id_accepts_partner_without_customer_tag(self):
        partner_no_tag = self.env["res.partner"].create({"name": "FF75 Partner No Tag"})
        master = self.env["freight.sea.job"].create({
            "record_level": "master",
            "freight_type": "export",
            "ship_mode": "lcl",
            "customer_id": partner_no_tag.id,
        })
        self.assertEqual(master.customer_id, partner_no_tag)


class TestFF75SeaSingleHousePerCommercialGroup(FreightTestBase):
    """Final FF-75 UAT follow-up: 1 commercial quotation group (root +
    seluruh currency variant) maksimal punya 1 freight.sea.job dengan
    record_level='house'. Berlaku murni untuk House -- Master tidak ikut
    rule ini."""

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

    def test_a_wizard_rejects_second_house_from_same_quotation(self):
        quotation = self._create_quotation()
        master = self._create_master()
        self._create_wizard(quotation, master).action_add_to_master()

        wizard2 = self._create_wizard(quotation, self._create_master())
        with self.assertRaises(UserError):
            wizard2.action_add_to_master()

        houses = self.env["freight.sea.job"].search([
            ("record_level", "=", "house"),
            ("source_quotation_id", "=", quotation.id),
        ])
        self.assertEqual(len(houses), 1,
            msg="Tetap hanya boleh ada 1 House dari Q1 setelah Add to Master kedua ditolak")

    def test_b_wizard_rejects_house_from_currency_variant_of_same_group(self):
        quotation = self._create_quotation()
        master = self._create_master()
        self._create_wizard(quotation, master).action_add_to_master()

        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        wizard2 = self._create_wizard(variant, self._create_master())
        with self.assertRaises(UserError):
            wizard2.action_add_to_master()

    def test_c_direct_orm_create_second_house_same_group_raises(self):
        quotation = self._create_quotation()
        master1 = self._create_master()
        house_vals = self.env["freight.sea.job"]._prepare_house_vals_from_quotation(quotation, master=master1)
        self.env["freight.sea.job"].create(house_vals)

        master2 = self._create_master()
        house2_vals = self.env["freight.sea.job"]._prepare_house_vals_from_quotation(quotation, master=master2)
        with self.assertRaises(ValidationError):
            self.env["freight.sea.job"].create(house2_vals)

    def test_c_write_into_duplicate_source_quotation_raises(self):
        """Constraint juga harus menangkap write(), bukan cuma create()."""
        quotation = self._create_quotation()
        master = self._create_master()
        house_vals = self.env["freight.sea.job"]._prepare_house_vals_from_quotation(quotation, master=master)
        self.env["freight.sea.job"].create(house_vals)

        other_master = self._create_master()
        other_house = self._create_hbl(
            record_level="house", master_job_id=other_master.id,
            freight_type="export", ship_mode="lcl",
        )
        with self.assertRaises(ValidationError):
            other_house.write({"source_quotation_id": quotation.id})

    def test_d_two_different_quotations_same_lcl_master_valid(self):
        quotation1 = self._create_quotation()
        quotation2 = self._create_quotation()
        master = self._create_master(ship_mode="lcl")

        self._create_wizard(quotation1, master).action_add_to_master()
        self._create_wizard(quotation2, master).action_add_to_master()

        self.assertEqual(len(master.house_job_ids), 2)

    def test_fcl_max_one_house_rule_still_independent(self):
        """Sea FCL max-1-House (jumlah total House di Master) tetap
        berbeda dari rule baru (1 quotation/commercial group -> max 1
        House) -- FCL master kedua Quotation BERBEDA tetap ditolak oleh
        rule FCL, bukan oleh rule baru ini."""
        quotation1 = self._create_quotation()
        quotation2 = self._create_quotation()
        master = self._create_master(ship_mode="fcl")

        self._create_wizard(quotation1, master).action_add_to_master()
        wizard2 = self._create_wizard(quotation2, master)
        with self.assertRaises(UserError):
            wizard2.action_add_to_master()

    def test_button_hidden_after_house_exists(self):
        quotation = self._create_quotation()
        self.assertEqual(quotation.sea_job_count, 0)
        master = self._create_master()
        self._create_wizard(quotation, master).action_add_to_master()
        quotation.invalidate_recordset(["sea_job_count"])
        self.assertEqual(quotation.sea_job_count, 1)


class TestFF75AirSingleHousePerCommercialGroup(FreightTestBase):
    """Mirror TestFF75SeaSingleHousePerCommercialGroup untuk Air."""

    def _create_air_quotation(self, **kwargs):
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "air",
            "freight_type": "export",
            "partner_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def _create_air_master(self, **kwargs):
        vals = {
            "shipment_type": "master",
            "freight_type": "export",
            "company_id": self.env.company.id,
        }
        vals.update(kwargs)
        return self.env["freight.air.job"].create(vals)

    def _create_wizard(self, quotation, master):
        return self.env["freight.air.add.to.master.wizard"].create({
            "quotation_id": quotation.id,
            "freight_type": quotation.freight_type,
            "company_id": quotation.company_id.id,
            "master_job_id": master.id,
        })

    def test_a_wizard_rejects_second_house_from_same_quotation(self):
        quotation = self._create_air_quotation()
        master = self._create_air_master()
        self._create_wizard(quotation, master).action_add_to_master()

        wizard2 = self._create_wizard(quotation, self._create_air_master())
        with self.assertRaises(UserError):
            wizard2.action_add_to_master()

        houses = self.env["freight.air.job"].search([
            ("shipment_type", "=", "house"),
            ("source_quotation_id", "=", quotation.id),
        ])
        self.assertEqual(len(houses), 1)

    def test_b_wizard_rejects_house_from_currency_variant_of_same_group(self):
        quotation = self._create_air_quotation()
        master = self._create_air_master()
        self._create_wizard(quotation, master).action_add_to_master()

        variant_result = quotation.action_create_currency_variant()
        variant = self.env["sale.order"].browse(variant_result["res_id"])

        wizard2 = self._create_wizard(variant, self._create_air_master())
        with self.assertRaises(UserError):
            wizard2.action_add_to_master()

    def test_c_direct_orm_create_second_house_same_group_raises(self):
        quotation = self._create_air_quotation()
        master1 = self._create_air_master()
        house_vals = self.env["freight.air.job"]._prepare_house_vals_from_quotation(quotation, master=master1)
        self.env["freight.air.job"].create(house_vals)

        master2 = self._create_air_master()
        house2_vals = self.env["freight.air.job"]._prepare_house_vals_from_quotation(quotation, master=master2)
        with self.assertRaises(ValidationError):
            self.env["freight.air.job"].create(house2_vals)

    def test_c_write_into_duplicate_source_quotation_raises(self):
        quotation = self._create_air_quotation()
        master = self._create_air_master()
        house_vals = self.env["freight.air.job"]._prepare_house_vals_from_quotation(quotation, master=master)
        self.env["freight.air.job"].create(house_vals)

        other_master = self._create_air_master()
        other_house = self.env["freight.air.job"].create({
            "shipment_type": "house",
            "master_job_id": other_master.id,
            "freight_type": "export",
        })
        with self.assertRaises(ValidationError):
            other_house.write({"source_quotation_id": quotation.id})

    def test_d_two_different_quotations_same_master_valid(self):
        quotation1 = self._create_air_quotation()
        quotation2 = self._create_air_quotation()
        master = self._create_air_master()

        self._create_wizard(quotation1, master).action_add_to_master()
        self._create_wizard(quotation2, master).action_add_to_master()

        self.assertEqual(len(master.house_job_ids), 2)

    def test_direct_awb_not_subject_to_single_house_rule(self):
        """Direct AWB (shipment_type='direct') tidak ikut rule ini sama
        sekali, meski punya source_quotation_id yang sama dengan House lain
        di commercial group yang sama."""
        quotation = self._create_air_quotation()
        master = self._create_air_master()
        self._create_wizard(quotation, master).action_add_to_master()

        direct = self.env["freight.air.job"].create({
            "shipment_type": "direct",
            "freight_type": "export",
            "source_quotation_id": quotation.id,
        })
        self.assertTrue(direct.exists())

    def test_button_hidden_after_house_exists(self):
        quotation = self._create_air_quotation()
        self.assertEqual(quotation.air_job_count, 0)
        master = self._create_air_master()
        self._create_wizard(quotation, master).action_add_to_master()
        quotation.invalidate_recordset(["air_job_count"])
        self.assertEqual(quotation.air_job_count, 1)
