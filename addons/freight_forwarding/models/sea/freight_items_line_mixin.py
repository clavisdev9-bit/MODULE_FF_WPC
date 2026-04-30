from odoo import fields, models


class SeaFreightItemsLineMixin(models.AbstractModel):
    _name = "freight.sea.items.line.mixin"
    _description = "Sea Freight Items Line Mixin"

    # Item details
    article = fields.Char(string="Article")
    type = fields.Char(string="Type")
    cant = fields.Integer(string="Cant.")

    # Dimensions
    length = fields.Float(string="Length (cm)")
    width = fields.Float(string="Width (cm)")
    height = fields.Float(string="Height (cm)")
    volume = fields.Float(string="Volume (CBM)")
    gross_weight = fields.Float(string="Gross Weight (Kg)")
