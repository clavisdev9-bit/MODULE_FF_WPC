
from odoo import fields, models

class FreightAirCargoInfoMixin(models.AbstractModel):
    _name = 'freight.air.cargo.info.mixin'
    _description = 'Air Freight Cargo Info Mixin'

    wt_val = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect')
    ], string='Wt/Val ?')
    
    pcs = fields.Integer(string='Pcs/Rcp')
    uom_id = fields.Many2one('uom.uom', string='UOM')
    gross_weight = fields.Float(string='Gross Weight')
    charge_weight = fields.Float(string='Charge Weight')
    commodity_id = fields.Many2one('freight.commodity', string='Commodity')
    other = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect')
    ], string='Other')

    total_dimension = fields.Float(string='Total Dimension', compute='_compute_cargo_totals', store=True)
    total_m3 = fields.Float(string='Total M3', compute='_compute_cargo_totals', store=True)
    total_vol_weight = fields.Float(string='Total Vol Wt', compute='_compute_cargo_totals', store=True)
    volumetric_weight = fields.Float(string='Volumetric Weight', compute='_compute_cargo_totals', store=True)
    total_pcs = fields.Integer(string='Total Pcs', compute='_compute_cargo_totals', store=True)

    # To be overridden by concrete models to calculate the dimensions
    def _compute_cargo_totals(self):
        for rec in self:
            rec.total_dimension = 0.0
            rec.total_m3 = 0.0
            rec.total_vol_weight = 0.0
            rec.volumetric_weight = 0.0
            rec.total_pcs = 0
