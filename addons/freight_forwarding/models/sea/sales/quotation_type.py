from odoo import fields, models


class SeaQuotationType(models.Model):
    _name = "freight.quotation.type"
    _description = "Freight Quotation Type"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code")
    description = fields.Text(string="Description")
