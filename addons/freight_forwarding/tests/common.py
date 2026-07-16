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
            "name": "Test Vessel MV-001",
        })

        # Master data: Delivery Type
        cls.delivery_type = cls.env["freight.delivery.type"].create({
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
            "freight_type": "export",
            "partner_id": self.partner.id,
            "delivery_type_id": self.delivery_type.id,
            "commodity_id": self.commodity.id,
            "container_type": "fcl",
            "port_of_loading_id": self.port_loading.id,
            "port_of_discharge_id": self.port_discharge.id,
        }
        vals.update(kwargs)
        return self.env["freight.sea.quotation"].create(vals)

    def _create_booking(self, **kwargs):
        """Buat Sea Booking dengan default nilai yang valid."""
        FreightTestBase._booking_counter += 1
        vals = {
            "name": f"TEST-BOOK-{FreightTestBase._booking_counter:03d}",
            "freight_type": "export",
            "container_type": "fcl",
            "partner_id": self.partner.id,
            "port_of_loading_id": self.port_loading.id,
            "port_of_discharge_id": self.port_discharge.id,
            "vessel_id": self.vessel.id,
            "delivery_type_id": self.delivery_type.id,
        }
        vals.update(kwargs)
        return self.env["freight.sea.booking"].create(vals)

    def _create_hbl(self, booking=None, **kwargs):
        """Buat Sea HBL dengan default nilai yang valid."""
        FreightTestBase._hbl_counter += 1
        vals = {
            "hbl_no": f"TEST-HBL-{FreightTestBase._hbl_counter:03d}" if "hbl_no" not in kwargs else kwargs["hbl_no"],
            "freight_type": "export",
            "container_type": "fcl",
        }
        if "hbl_no" in kwargs and kwargs["hbl_no"] is False:
            vals.pop("hbl_no")
            
        if booking:
            vals["booking_id"] = booking.id
        vals.update(kwargs)
        return self.env["freight.sea.hbl"].create(vals)

    def _create_booking_cargo_info(self, booking, **kwargs):
        """Buat satu baris cargo info untuk booking."""
        vals = {
            "booking_id": booking.id,
            "uom": "box",
            "quantity": 10,
        }
        vals.update(kwargs)
        return self.env["freight.sea.booking.cargo.info"].create(vals)
