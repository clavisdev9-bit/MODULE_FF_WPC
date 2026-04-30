from odoo import fields, models


class SeaHBLVesselDetails(models.Model):
    _name = "freight.sea.hbl.vessel.details"
    _description = "Sea Jobsheet Vessel Details"
    _inherit = "freight.sea.vessel.details.mixin"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet",
        ondelete="cascade",
        required=True,
    )