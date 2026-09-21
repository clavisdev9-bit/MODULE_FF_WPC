from odoo import fields, models


class FreightTransportDocumentCode(models.Model):
    """FF-78: generic Code Master (Air AWB Code / Sea B/L Code), shared
    across Air and Sea via `transport_mode` -- mirroring the FF-76 pattern
    used for `freight.transport.document` (canonical shared model, UI
    terminology kept separate per transport mode).

    This model is DELIBERATELY standalone: it has no relation to Airline,
    Shipping Line, or `freight.transport.document`. It is not a lookup
    table validated against actual document numbers -- it is independent
    master/config data (per FF-78 scope).

    Inventory/usage fields (reorder qty, MTD/YTD usage, last use/receipt
    date, etc.) are plain editable Char/Integer/Date/Boolean fields for
    now -- their exact calculation/lifecycle is not yet confirmed, so
    there is no auto-calculation, no derivation from Document Master, and
    no receipt/release/scheduler logic here.
    """

    _name = "freight.transport.document.code"
    _description = "Transport Document Code"
    _rec_name = "code"

    _sql_constraints = [
        ("code_uniq", "unique(transport_mode, code)",
         "Code harus unik per Transport Mode."),
    ]

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", size=50)
    transport_mode = fields.Selection(
        [("air", "Air"), ("sea", "Sea")],
        string="Transport Mode",
        required=True,
        default="air",
    )

    reorder_qty = fields.Integer(string="Reorder Qty")
    qty_on_hand = fields.Integer(string="Qty On Hand")
    mtd_usage = fields.Integer(string="MTD Usage")
    ytd_usage = fields.Integer(string="YTD Usage")
    last_year_usage = fields.Integer(string="Last Year Usage")
    last_use_date = fields.Date(string="Last Use Date")
    last_receipt_date = fields.Date(string="Last Receipt Date")
    is_neutral = fields.Boolean(string="Neutral")
    check_digit = fields.Boolean(string="Check Digit")
    document_length = fields.Integer(string="Document Length")
