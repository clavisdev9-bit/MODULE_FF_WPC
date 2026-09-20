"""
Shared fixtures and base class for freight_forwarding tests.

Usage:
    class TestMyFeature(FreightTestBase):
        def test_something(self):
            booking = self._create_booking()
            ...
"""
from odoo.tests.common import TransactionCase


class FreightTestBase(TransactionCase):
    """Base class untuk semua test modul freight_forwarding.

    Menyediakan factory methods untuk membuat test data secara konsisten.
    Semua data dibuat ulang tiap test dan di-rollback otomatis oleh TransactionCase.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Master data: Partner (Customer)
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
            "is_company": True,
        })

        # Master data: Port
        cls.port_loading = cls.env["freight.port"].create({
            "name": "Tanjung Priok",
            "code": "IDJKT",
        })
        cls.port_discharge = cls.env["freight.port"].create({
            "name": "Singapore",
            "code": "SGSIN",
        })

        # Master data: Vessel
        cls.vessel = cls.env["freight.vessel"].create({
            "code": "MV001",
            "name": "Test Vessel MV-001",
        })

        # Master data: Delivery Type (account.incoterms native Odoo)
        cls.delivery_type = cls.env["account.incoterms"].search([("code", "=", "DTD")], limit=1)
        if not cls.delivery_type:
            cls.delivery_type = cls.env["account.incoterms"].create({
                "code": "DTD",
                "name": "Door to Door",
            })

        # Master data: Commodity
        cls.commodity = cls.env["freight.commodity"].create({
            "code": "GEN",
            "name": "General Cargo",
        })

        # Master data: Container Type
        cls.container_type = cls.env["freight.container.type"].create({
            "code": "20GP",
            "name": "20ft General Purpose",
        })

    # =========================================================
    # Factory Methods
    # =========================================================
    
    _booking_counter = 0
    _hbl_counter = 0

    def _create_quotation(self, **kwargs):
        """Buat Sea Quotation dengan default nilai yang valid."""
        vals = {
            "is_freight_quotation": True,
            "freight_business_type": "sea",
            "freight_type": "export",
            "partner_id": self.partner.id,
            "delivery_type_id": self.delivery_type.id,
            "commodity_id": self.commodity.id,
            "sea_ship_mode": "fcl",
            "port_of_loading_id": self.port_loading.id,
            "port_of_discharge_id": self.port_discharge.id,
        }
        vals.update(kwargs)
        return self.env["sale.order"].create(vals)

    def _resolve_source_quotation_id(self, quotation_id):
        """FF-73: resolve root quotation (commercial group anchor) dari id
        quotation/variant apa pun -- dipakai fixture helper supaya
        source_quotation_id (canonical) terisi selaras dengan arsitektur
        commercial group, bukan cuma sale_order_ids (compatibility mirror)."""
        quotation = self.env["sale.order"].browse(quotation_id)
        root = quotation.original_quotation_id or quotation
        return root.id

    def _create_booking(self, **kwargs):
        """Buat Sea Booking dengan default nilai yang valid.

        `quotation_id=<sale.order record atau id>` diterima sebagai shortcut.
        FF-73: selain `sale_order_ids` (compatibility mirror), ini juga
        mengisi `source_quotation_id` (canonical commercial-group anchor) --
        supaya fixture merepresentasikan arsitektur yang sama dengan
        `_action_convert_to_booking_direct_sea` produksi, bukan cuma jalur
        legacy sale_order_ids yang sudah tidak jadi source of truth resolver.
        """
        FreightTestBase._booking_counter += 1
        quotation_id = kwargs.pop("quotation_id", None)
        vals = {
            "name": f"TEST-BOOK-{FreightTestBase._booking_counter:03d}",
            "freight_type": "export",
            "ship_mode": "fcl",
            "partner_id": self.partner.id,
            "port_of_loading_id": self.port_loading.id,
            "port_of_discharge_id": self.port_discharge.id,
            "feeder_vessel_id": self.vessel.id,
            "feeder_voyage_no": "V001",
            "delivery_type_id": self.delivery_type.id,
        }
        vals.update(kwargs)
        if quotation_id and "sale_order_ids" not in kwargs:
            vals["sale_order_ids"] = [(6, 0, [quotation_id])]
        if quotation_id and "source_quotation_id" not in kwargs:
            vals["source_quotation_id"] = self._resolve_source_quotation_id(quotation_id)
        return self.env["freight.sea.booking"].create(vals)

    def _create_hbl(self, booking=None, **kwargs):
        """Buat Sea HBL dengan default nilai yang valid.

        `quotation_id=<sale.order record atau id>` diterima sebagai shortcut
        untuk flow direct-import (Jobsheet langsung dari quotation, tanpa
        booking). FF-73: selain `sale_order_ids` (compatibility mirror), ini
        juga mengisi `source_quotation_id` (canonical direct-flow reference --
        lihat `action_convert_to_jobsheet_direct_sea` produksi).

        `booking=<freight.sea.booking record>` (flow via Booking) HANYA
        mengisi `booking_id` -- source_quotation_id/sale_order_ids pada HBL
        SENGAJA dibiarkan kosong, karena resolver production
        (`_get_source_quotation` / `_get_commercial_group_jobsheets`) untuk
        flow ini menemukan root lewat `booking_id.source_quotation_id`, bukan
        lewat field HBL sendiri. Mengisinya manual di sini hanya akan
        menutupi kalau resolver production berhenti membaca lewat booking.

        FF-75 follow-up: House WAJIB punya Master (constraint keras di
        model). Kalau caller tidak eksplisit minta `record_level="master"`
        atau kasih `master_job_id` sendiri, factory ini otomatis membuatkan
        Master shell supaya tetap valid terhadap constraint tersebut --
        murni buat kenyamanan fixture, bukan behavior production.
        """
        FreightTestBase._hbl_counter += 1
        quotation_id = kwargs.pop("quotation_id", None)
        vals = {
            "hbl_no": f"TEST-HBL-{FreightTestBase._hbl_counter:03d}" if "hbl_no" not in kwargs else kwargs["hbl_no"],
            "freight_type": "export",
            "ship_mode": "fcl",
        }
        if "hbl_no" in kwargs and kwargs["hbl_no"] is False:
            vals.pop("hbl_no")

        if booking:
            vals["booking_id"] = booking.id
        vals.update(kwargs)
        if quotation_id and "sale_order_ids" not in kwargs:
            vals["sale_order_ids"] = [(6, 0, [quotation_id])]
        if quotation_id and "source_quotation_id" not in kwargs:
            vals["source_quotation_id"] = self._resolve_source_quotation_id(quotation_id)

        if vals.get("record_level", "house") == "house" and not vals.get("master_job_id"):
            auto_master = self.env["freight.sea.job"].create({
                "record_level": "master",
                "freight_type": vals.get("freight_type") or "export",
                "ship_mode": vals.get("ship_mode") or "fcl",
                "company_id": vals.get("company_id") or self.env.company.id,
            })
            vals["master_job_id"] = auto_master.id
        return self.env["freight.sea.job"].create(vals)

    def _create_booking_cargo_info(self, booking, **kwargs):
        """Buat satu baris cargo info untuk booking."""
        vals = {
            "booking_id": booking.id,
            "uom": "box",
            "quantity": 10,
        }
        vals.update(kwargs)
        return self.env["freight.sea.booking.cargo.info"].create(vals)
