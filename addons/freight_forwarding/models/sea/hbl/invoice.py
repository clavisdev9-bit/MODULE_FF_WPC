from odoo import fields, models


class SeaHBLInvoice(models.Model):
    _name = "freight.sea.hbl.invoice"
    _description = "Sea Jobsheet Invoice"
    _rec_name = "hbl_id"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    invoice_reference = fields.Many2one("account.move", string="Invoice Reference")
