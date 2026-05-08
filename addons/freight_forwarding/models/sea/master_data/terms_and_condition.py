from odoo import fields, models


class FreightTermsAndConditions(models.Model):
    _name = "freight.terms.conditions"
    _description = "Freight Terms and Conditions"
    _rec_name = "name"

    _sql_constraints = [
        (
            "code_unique",
            "UNIQUE(code)",
            "Terms Code must be unique!",
        ),
    ]

    code = fields.Char(string="Terms Code", required=True)
    name = fields.Char(string="Terms and Conditions Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
