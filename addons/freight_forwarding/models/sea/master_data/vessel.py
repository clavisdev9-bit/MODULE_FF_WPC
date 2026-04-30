from odoo import fields, models


class FreightVessel(models.Model):
    _name = "freight.vessel"
    _description = "Freight Vessel"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Vessel Code must be unique!")
    ]

    code = fields.Char(string="Vessel Code")
    name = fields.Char(string="Vessel Name", required=True)
    voyage_no = fields.Char(string="Voyage No.")
    imo_number = fields.Char(string="IMO Number")
    flag = fields.Char(string="Flag")
    active = fields.Boolean(string="Active", default=True)
