from odoo import fields, models


class SeaBookingExtraInfo(models.Model):
    _name = "freight.sea.booking.extra.info"
    _description = "Sea Booking Extra Info"
    _rec_name = "booking_id"

    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking No.",
        ondelete="cascade",
        required=True,
    )
    do_date = fields.Date(string="DO Date")
    do_date_collecting = fields.Date(string="DO Collecting Date")
    do_transit = fields.Char(string="DO Transit")
    do_mode_transport = fields.Char(string="DO Mode Transport")
    do_quote_reference = fields.Char(string="DO Quote Reference")
    do_peb_number = fields.Char(string="PEB Number")
    do_npe_date = fields.Date(string="NPE Date")
    do_po_number = fields.Char(string="PO Number")
    do_supplier_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        domain="[('category_id.name', '=', 'Vendor')]",
    )
    do_product_name = fields.Char(string="Product Name")
    do_serial_number_doc_number = fields.Char(string="Serial / Document Number")
