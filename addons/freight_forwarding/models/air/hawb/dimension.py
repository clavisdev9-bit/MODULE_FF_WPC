from odoo import fields, models

class FreightAirHawbDimension(models.Model):
    _name = 'freight.air.hawb.dimension'
    _inherit = 'freight.air.dimension.mixin'
    _description = 'Air HAWB Dimension'

    hawb_id = fields.Many2one('freight.air.hawb', string='Air Jobsheet (HAWB)', ondelete='cascade', required=True)
