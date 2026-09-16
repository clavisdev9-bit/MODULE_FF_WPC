from odoo import fields, models

class FreightPort(models.Model):
    _name = "freight.port"
    _description = "Freight Port"
    _rec_name = "name"

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Port Code must be unique!")
    ]

    code = fields.Char(string="Port Code", required=True, size=5)
    name = fields.Char(string="Port Name", required=True)
    country_id = fields.Many2one("res.country", string="Country")
    dg_cargo = fields.Boolean(string="DG Cargo")
    symbol = fields.Char(string="Symbol")
    group_code = fields.Char(string="Group Code")
    region_code = fields.Char(string="Region Code")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    active = fields.Boolean(string='Active', default=True)

    destination_ids = fields.One2many(
        'freight.port.destination', 'port_id', string='Destinations',
    )