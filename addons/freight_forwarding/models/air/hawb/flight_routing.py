from odoo import fields, models

class FreightAirHawbFlightRouting(models.Model):
    _name = 'freight.air.hawb.flight.routing'
    _inherit = 'freight.air.flight.routing.mixin'
    _description = 'Air HAWB Flight Routing'

    hawb_id = fields.Many2one('freight.air.hawb', string='Air Jobsheet (HAWB)', ondelete='cascade', required=True)
    eta_date = fields.Date(string='ETA')
