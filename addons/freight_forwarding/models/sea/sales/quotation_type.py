from odoo import fields, models


class SeaQuotationType(models.Model):
    _name = "freight.quotation.type"
    _description = "Freight Quotation Type"
    _rec_name = "description"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Quotation Type Code must be unique!")
    ]

    code = fields.Char(string="Quote Type")
    description = fields.Text(string="Quote Type Description")
    active = fields.Boolean(string="Active", default=True)
