from odoo import models, fields


class AirExtraInfo(models.Model):
    _name = 'freight.air.extra.info'
    _description = 'Air Extra Info'
    _rec_name = 'do_number'

    mawb_id = fields.Many2one(
        'freight.air.mawb',
        string='MAWB No',
        required=True,
        ondelete='cascade'
    )
    do_number = fields.Char(string='D/O Number', required=True)
    do_date = fields.Date(string='D/O Date')
    do_date_collecting = fields.Date(string='D/O Date Collecting')
    do_transit = fields.Boolean(string='D/O Transit')
    do_mode_transport = fields.Char(string='D/O Mode Transport')
    do_quote_reference = fields.Char(string='D/O Quote Reference')

    do_peb_number = fields.Char(string='D/O PEB Number')
    do_npe_date = fields.Date(string='D/O NPE Date')
    do_po_number = fields.Char(string='D/O PO Number')
    do_supplier = fields.Many2one(
        'res.partner', 
        string='D/O Supplier',
        domain="[('category_id.name', '=', 'D/O Supplier')]"
    )
    do_product_name = fields.Many2one(
        'product.template',
        string='D/O Product Name'
    )
    do_serial_number_doc_number = fields.Char(string='D/O Serial Number Doc Number')