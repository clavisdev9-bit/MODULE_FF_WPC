"""Test untuk Sea HBL model — khususnya behavior cascade/set null."""
from .common import FreightTestBase


class TestSeaHblOndelete(FreightTestBase):
    """
    Verifikasi menghapus quotation tidak ikut menghapus HBL operasional.

    Relasi HBL ke quotation sekarang lewat sale_order_ids (Many2many, bukan
    Many2one quotation_id lagi — lihat FF-71). Many2many secara natural tidak
    bisa cascade-delete record di sisi lain, jadi behavior "set null" yang
    dulu dijamin lewat ondelete="set null" sekarang otomatis berlaku lewat
    penghapusan baris relasi M2M.
    """

    def test_delete_quotation_does_not_delete_hbl(self):
        """
        [BUG REPRODUCTION] Menghapus quotation tidak menghapus HBL.

        Sebelum fix (cascade M2O): menghapus quotation → HBL ikut terhapus.
        Setelah fix (M2M sale_order_ids): HBL tetap ada, relasinya hilang.
        """
        # Arrange: buat HBL langsung dari quotation (import flow)
        quotation = self._create_quotation(freight_type="import")
        hbl = self._create_hbl(
            freight_type="import",
            quotation_id=quotation.id,
        )
        hbl_id = hbl.id

        # Act: hapus quotation
        quotation.unlink()

        # Assert: HBL masih ada
        surviving_hbl = self.env["freight.sea.hbl"].browse(hbl_id)
        self.assertTrue(surviving_hbl.exists(),
            msg="HBL harus tetap ada setelah quotation dihapus")

        # Assert: relasi ke quotation hilang, bukan cascade hapus HBL
        self.assertFalse(surviving_hbl.sale_order_ids,
            msg="sale_order_ids harus kosong setelah quotation dihapus")

    def test_delete_booking_deletes_hbl(self):
        """Menghapus booking HARUS menghapus HBL (cascade tetap berlaku di booking_id)."""
        booking = self._create_booking()
        hbl = self._create_hbl(booking=booking)
        hbl_id = hbl.id

        booking.unlink()

        surviving_hbl = self.env["freight.sea.hbl"].browse(hbl_id)
        self.assertFalse(surviving_hbl.exists(),
            msg="HBL harus terhapus saat booking-nya dihapus (cascade)")


class TestSeaHblSequence(FreightTestBase):
    """Verifikasi auto-generate nomor HBL dan Job No."""

    def test_hbl_no_auto_generated(self):
        """hbl_no di-generate otomatis saat tidak diisi."""
        # Pass hbl_no=False secara eksplisit untuk trigger auto-generate
        hbl = self._create_hbl(hbl_no=False)
        self.assertTrue(hbl.hbl_no,
            msg="hbl_no harus ter-generate otomatis")

    def test_hbl_no_unique_per_record(self):
        """Dua HBL yang dibuat berurutan harus punya nomor berbeda."""
        hbl1 = self._create_hbl(hbl_no=False)
        hbl2 = self._create_hbl(hbl_no=False)

        self.assertNotEqual(hbl1.hbl_no, hbl2.hbl_no,
            msg="Setiap HBL harus punya nomor unik")

    def test_hbl_no_manual_not_overridden(self):
        """Jika hbl_no sudah diisi manual, tidak di-override oleh sequence."""
        hbl = self._create_hbl(hbl_no="MANUAL-001")
        self.assertEqual(hbl.hbl_no, "MANUAL-001",
            msg="hbl_no manual tidak boleh di-override")

    def test_job_no_auto_generated(self):
        """job_no di-generate otomatis saat tidak diisi."""
        hbl = self._create_hbl(job_no=False)
        self.assertTrue(hbl.job_no,
            msg="job_no harus ter-generate otomatis")


class TestSeaBlInfoNotifySameAsConsignee(FreightTestBase):
    """Verifikasi fitur notify_same_as_consignee pada FreightBlInfoMixin (FF-52)."""

    def test_onchange_notify_same_as_consignee(self):
        """Saat notify_same_as_consignee diaktifkan, notify_party_id otomatis sama dengan consignee_id."""
        hbl = self._create_hbl(consignee_id=self.partner.id)
        hbl.notify_same_as_consignee = True
        hbl._onchange_notify_same_as_consignee()
        self.assertEqual(hbl.notify_party_id, self.partner,
            msg="notify_party_id harus otomatis mengikuti consignee_id saat notify_same_as_consignee=True")

    def test_onchange_consignee_updates_notify_party_when_active(self):
        """Saat consignee_id berubah dan notify_same_as_consignee=True, notify_party_id ikut ter-update."""
        partner_other = self.env["res.partner"].create({"name": "Consignee Baru"})
        hbl = self._create_hbl(consignee_id=self.partner.id)
        hbl.notify_same_as_consignee = True
        hbl._onchange_notify_same_as_consignee()

        hbl.consignee_id = partner_other
        hbl._onchange_notify_same_as_consignee()
        self.assertEqual(hbl.notify_party_id, partner_other,
            msg="notify_party_id harus sinkron dengan consignee_id baru saat notify_same_as_consignee aktif")


class TestSeaHblYard(FreightTestBase):
    """Verifikasi related yard_code dan yard_address di HBL (FF-53)."""

    def test_hbl_yard_code_and_address_related(self):
        """yard_code dan yard_address di Jobsheet otomatis terisi dari Yard (stock.warehouse)."""
        warehouse = self.env["stock.warehouse"].create({
            "name": "Test Yard Warehouse",
            "code": "TYW01",
        })
        hbl = self._create_hbl(yard_id=warehouse.id)
        self.assertEqual(hbl.yard_code, "TYW01")
        if warehouse.partner_id.contact_address:
            self.assertEqual(hbl.yard_address, warehouse.partner_id.contact_address)


