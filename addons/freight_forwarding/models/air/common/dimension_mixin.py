from odoo import api, fields, models

class FreightAirDimensionMixin(models.AbstractModel):
    _name = 'freight.air.dimension.mixin'
    _description = 'Air Freight Dimension Mixin'

    sequence = fields.Integer(string='S/No', default=10)
    qty = fields.Integer(string='Pcs/Rcp', required=True, default=1)
    uom_id = fields.Many2one('uom.uom', string='UOM')
    length = fields.Float(string='Length', required=True, default=0.0)
    width = fields.Float(string='Width', required=True, default=0.0)
    height = fields.Float(string='Height', required=True, default=0.0)
    
    volume = fields.Float(string='Dimension', compute='_compute_volume', store=True)
    
    @api.depends('qty', 'length', 'width', 'height')
    def _compute_volume(self):
        for rec in self:
            rec.volume = rec.qty * rec.length * rec.width * rec.height
