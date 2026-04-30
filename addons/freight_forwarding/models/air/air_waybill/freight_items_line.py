from odoo import models, fields

class AirMAWBItemsLine(models.Model):
    _name = 'freight.air.mawb.items.line'
    _description = 'Freight Air MAWB Items Line'
    _rec_name = 'package_details_id'

    package_details_id = fields.Many2one(
        'freight.air.mawb.package.details',
        string='Package Details',
        required=True,
        ondelete='cascade'
    )
    
    # Item Details
    article = fields.Char(string="Article")
    type = fields.Char(string="Type")
    cant = fields.Integer(string="Cant.")

    # Dimension
    length = fields.Float(string="Length (cm)")
    width = fields.Float(string="Width (cm)")
    height = fields.Float(string="Height (cm)")
    volume = fields.Float(string="Volume (CBM)")
    gross_weight = fields.Float(string="Gross Weight (Kg)")