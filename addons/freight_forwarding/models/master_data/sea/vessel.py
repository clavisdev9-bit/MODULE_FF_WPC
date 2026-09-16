from odoo import fields, models


class FreightVessel(models.Model):
    _name = "freight.vessel"
    _description = "Freight Vessel"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Vessel Code must be unique!")
    ]

    code = fields.Char(string="Vessel Code", required=True, size=12)
    name = fields.Char(string="Vessel Name", required=True)
    short_name = fields.Char(string="Short Name")
    vessel_type = fields.Char(string="Vessel Type")
    vessel_classification = fields.Char(string="Vessel Classification")
    imo_number = fields.Char(string="IMO Number")
    shipping_line_id = fields.Many2one(
        "res.partner", string="Shipping Line",
        domain="[('category_id.freight_role_code', '=', 'shipping_line')]",
    )
    ship_owner_id = fields.Many2one("res.partner", string="Ship Owner")
    nrt = fields.Float(string="NRT")
    grt = fields.Float(string="GRT")
    year_built = fields.Integer(string="Year Built")
    flag = fields.Many2one("res.country", string="Flag")
    active = fields.Boolean(string="Active", default=True)
