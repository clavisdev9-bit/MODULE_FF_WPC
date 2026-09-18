from odoo import api, fields, models

class FreightAirShipmentInfoMixin(models.AbstractModel):
    _name = 'freight.air.shipment.info.mixin'
    _description = 'Air Freight Shipment Info Mixin'

    departure_id = fields.Many2one('freight.airport', string='Airport of Departure')
    destination_id = fields.Many2one('freight.airport', string='Airport of Destination')
    destination_date = fields.Date(string='Destination Date')
    origin_country_id = fields.Many2one('res.country', string='Country of Origin', default=lambda self: self.env.ref('base.id', raise_if_not_found=False) or self.env.company.country_id)
    ship_mode = fields.Selection([
        ('routing_order', 'ROUTING ORDER'),
        ('free_hands', 'FREE HANDS'),
        ('transit', 'TRANSIT')
    ], string='Ship Mode')
    shipment_type = fields.Selection([
        ('direct', 'Direct'),
        ('house', 'House'),
        ('master', 'Master')
    ], string='Shipment Type', default='house', tracking=True)

    delivery_type = fields.Many2one('account.incoterms', string='Delivery Type')
    other_delivery = fields.Selection([('P', 'Prepaid'), ('C', 'Collect')], string='Other')
    service_level = fields.Selection([
        ('p1', 'P1'),
        ('p2', 'P2'),
        ('p3', 'P3'),
        ('p4', 'P4'),
    ], string='Service Level')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    currency_rate = fields.Float(string='Currency Rate', default=1.0)
    wt_val_billing_party_id = fields.Many2one('res.partner', string='Billing Party (Wt/Val)')
    other_billing_party_id = fields.Many2one('res.partner', string='Billing Party (Other)')

    collect_currency_id = fields.Many2one('res.currency', string='Collect Currency')
    collect_currency_rate = fields.Float(string='Collect Currency Rate', default=1.0)

    declared_value_carriage = fields.Char(string='Declared Value for Carriage', default='N.V.D')
    custom_currency_id = fields.Many2one('res.currency', string='Customs Currency')
    declared_value_customs = fields.Char(string='Customs Declared Value', default='N.C.V')
    customs_local_amt = fields.Float(string='Customs Local Amt')
    is_dg_cargo = fields.Boolean(string='DG Cargo')

    insurance_currency_id = fields.Many2one('res.currency', string='Insurance Currency')
    insurance_amount = fields.Float(string='Insurance Amount')
    insurance_local_amount = fields.Float(string='Insurance Local Amount')

    handling_information_id = fields.Many2one('freight.air.handling.information', string='Handling Info Template')
    handling_information = fields.Text(string='Handling Information')
    accounting_information = fields.Text(string='Accounting Information')
    permit_no = fields.Char(string='Permit No.')
    print_dimension = fields.Boolean(string='Print Dimension', default=True)

    @api.onchange('handling_information_id')
    def _onchange_handling_information_id(self):
        if self.handling_information_id:
            self.handling_information = self.handling_information_id.description or self.handling_information_id.name
