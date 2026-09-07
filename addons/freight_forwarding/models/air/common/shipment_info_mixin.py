from odoo import fields, models

class FreightAirShipmentInfoMixin(models.AbstractModel):
    _name = 'freight.air.shipment.info.mixin'
    _description = 'Air Freight Shipment Info Mixin'

    departure_id = fields.Many2one('freight.airport', string='Airport of Departure')
    destination_id = fields.Many2one('freight.airport', string='Airport of Destination')
    origin_country_id = fields.Many2one('res.country', string='Country of Origin', default=lambda self: self.env.ref('base.id', raise_if_not_found=False) or self.env.company.country_id)
    
    ship_mode = fields.Selection([
        ('routing_order', 'ROUTING ORDER'),
        ('free_hands', 'FREE HANDS'),
        ('transit', 'TRANSIT')
    ], string='Ship Mode')
    shipment_type = fields.Selection([
        ('direct', 'DIRECT'),
        ('house', 'HOUSE'),
        ('coloader', 'CO-LOADER')
    ], string='Shipment Type', default='house')
    
    delivery_type = fields.Many2one('freight.delivery.type', string='Delivery Type')
    other_delivery = fields.Selection([('P', 'Prepaid'), ('C', 'Collect')], string='Other')
    service_level = fields.Char(string='Service Level')
