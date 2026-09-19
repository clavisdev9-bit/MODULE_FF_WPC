from odoo import fields, models

class FreightAirHawbDimension(models.Model):
    _name = 'freight.air.job.dimension'
    _inherit = 'freight.air.dimension.mixin'
    _description = 'Air HAWB Dimension'

    job_id = fields.Many2one('freight.air.job', string='Air Jobsheet (HAWB)', ondelete='cascade', required=True)
