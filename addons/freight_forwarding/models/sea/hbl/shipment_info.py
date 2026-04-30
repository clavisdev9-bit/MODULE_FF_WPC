from odoo import fields, models


class SeaHBLShipmentInfo(models.Model):
    _name = "freight.sea.hbl.shipment.info"
    _description = "Sea Jobsheet Shipment Info"
    _inherit = "freight.sea.shipment.info.mixin"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet",
        ondelete="cascade",
        required=True,
    )