from odoo import fields, models


class FreightAirHawbInvoice(models.Model):
    _name = "freight.air.hawb.invoice"
    _description = "Air Jobsheet Invoice"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
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


class FreightAirHawbDebitNote(models.Model):
    _name = "freight.air.hawb.debit.note"
    _description = "Air Jobsheet Debit Note"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    debit_note_reference = fields.Many2one("account.move", string="Debit Note Reference")


class FreightAirHawbCreditNote(models.Model):
    _name = "freight.air.hawb.credit.note"
    _description = "Air Jobsheet Credit Note"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    credit_note_reference = fields.Many2one("account.move", string="Credit Note Reference")


class FreightAirHawbProvisionCost(models.Model):
    _name = "freight.air.hawb.provision.cost"
    _description = "Air Jobsheet Provision Cost"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    provision_cost_reference = fields.Many2one("account.move", string="Provision Cost Reference")


class FreightAirHawbVendorInvoice(models.Model):
    _name = "freight.air.hawb.vendor.invoice"
    _description = "Air Jobsheet Vendor Invoice"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    vendor_invoice_reference = fields.Many2one("account.move", string="Vendor Invoice Reference")


class FreightAirHawbVendorDebitNote(models.Model):
    _name = "freight.air.hawb.vendor.debit.note"
    _description = "Air Jobsheet Vendor Debit Note"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    vendor_debit_note_reference = fields.Many2one("account.move", string="Vendor Debit Note Reference")


class FreightAirHawbVendorCreditNote(models.Model):
    _name = "freight.air.hawb.vendor.credit.note"
    _description = "Air Jobsheet Vendor Credit Note"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    vendor_credit_note_reference = fields.Many2one("account.move", string="Vendor Credit Note Reference")


class FreightAirHawbCashPurchase(models.Model):
    _name = "freight.air.hawb.cash.purchase"
    _description = "Air Jobsheet Cash Purchase"
    _rec_name = "hawb_id"

    hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    cash_purchase_reference = fields.Many2one("account.move", string="Cash Purchase Reference")
