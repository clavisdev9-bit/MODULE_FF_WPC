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
    freight_type = fields.Selection(
        related="hbl_id.freight_type",
        string="Type",
        store=True,
        readonly=True,
    )
    warehouse_location_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse Location",
    )