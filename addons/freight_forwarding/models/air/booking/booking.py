from odoo import models, fields, api, _

class FreightAirBooking(models.Model):
    _name = 'freight.air.booking'
    _description = 'Air Freight Booking'
    _inherit = [
        'mail.thread', 
        'mail.activity.mixin',
        'freight.air.awb.info.mixin',
        'freight.air.shipment.info.mixin',
        'freight.air.cargo.info.mixin'
    ]
    _order = 'id desc'

    name = fields.Char(string='Booking No.', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    booking_date = fields.Datetime(string='Booking Date', default=fields.Datetime.now, required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    
    freight_type = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export')
    ], string='Type', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    customer_reference = fields.Char(string='Customer Reference', tracking=True)
    
    telephone = fields.Char(string='Telephone', related='partner_id.phone', readonly=False, store=True)
    email = fields.Char(string='Email')
    is_nomination = fields.Boolean(string='Nomination Cargo')
    nomination_remark = fields.Char(string='Nomination Remark')
    booking_from = fields.Char(string='Booking From')

    payment_term_id = fields.Many2one('account.payment.term', string='Credit Term')
    salesman_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    quotation_id = fields.Many2one('sale.order', string='Quotation No.')

    booking_remark = fields.Text(string='Booking Remark')
    footnote = fields.Text(string='Footnote')

    # Job / AWB References
    job_no = fields.Char(string='Job No.')
    awb_no = fields.Char(string='Awb No.')
    mawb_no = fields.Char(string='Mawb No.')

    # Relational Tables
    flight_routing_ids = fields.One2many('freight.air.booking.flight.routing', 'booking_id', string='Flight Routings')
    dimension_ids = fields.One2many('freight.air.booking.dimension', 'booking_id', string='Dimensions')
    hawb_ids = fields.One2many('freight.air.hawb', 'booking_id', string='Air Jobsheets (HAWBs)')
    hawb_count = fields.Integer(string='Jobsheet Count', compute='_compute_hawb_count')

    def _compute_hawb_count(self):
        for rec in self:
            rec.hawb_count = len(rec.hawb_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('freight.air.booking') or _('New')
        return super(FreightAirBooking, self).create(vals_list)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.depends('dimension_ids.qty', 'dimension_ids.volume')
    def _compute_cargo_totals(self):
        for rec in self:
            rec.total_pcs = sum(rec.dimension_ids.mapped('qty'))
            total_vol = sum(rec.dimension_ids.mapped('volume'))
            rec.total_dimension = total_vol
            rec.total_m3 = total_vol / 1000000.0 if total_vol else 0.0
            rec.total_vol_weight = total_vol / 6000.0 if total_vol else 0.0
            rec.volumetric_weight = total_vol / 6000.0 if total_vol else 0.0

    def action_create_hawb(self):
        self.ensure_one()
        flight_lines = [
            (0, 0, {
                'airport_dest_id': r.airport_dest_id.id if r.airport_dest_id else False,
                'airline_id': r.airline_id.id if r.airline_id else False,
                'flight_no': r.flight_no,
                'flight_date': r.flight_date,
            }) for r in self.flight_routing_ids
        ]
        dimension_lines = [
            (0, 0, {
                'sequence': d.sequence,
                'qty': d.qty,
                'uom_id': d.uom_id.id if d.uom_id else False,
                'length': d.length,
                'width': d.width,
                'height': d.height,
            }) for d in self.dimension_ids
        ]

        hawb_vals = {
            'booking_id': self.id,
            'freight_type': self.freight_type,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'customer_ref': self.customer_reference,
            'is_nomination': self.is_nomination,
            'nomination_remark': self.nomination_remark,
            'term_payment': self.payment_term_id.id if self.payment_term_id else False,
            'salesman_id': self.salesman_id.id if self.salesman_id else False,
            'hawb_no': self.awb_no or False,
            'mawb_no': self.mawb_no or False,
            # Parties
            'shipper_id': self.shipper_id.id if self.shipper_id else False,
            'consignee_id': self.consignee_id.id if self.consignee_id else False,
            'notify_party_id': self.notify_party_id.id if self.notify_party_id else False,
            'coloader_id': self.coloader_id.id if self.coloader_id else False,
            'agent_id': self.agent_id.id if self.agent_id else False,
            'overseas_agent_id': self.overseas_agent_id.id if self.overseas_agent_id else False,
            # Shipment Info
            'departure_id': self.departure_id.id if self.departure_id else False,
            'destination_id': self.destination_id.id if self.destination_id else False,
            'origin_country_id': self.origin_country_id.id if self.origin_country_id else False,
            'ship_mode': self.ship_mode,
            'shipment_type': self.shipment_type,
            'delivery_type': self.delivery_type.id if self.delivery_type else False,
            'other_delivery': self.other_delivery,
            'service_level': self.service_level,
            # Cargo summary
            'wt_val': self.wt_val,
            'commodity_id': self.commodity_id.id if self.commodity_id else False,
            'gross_weight': self.gross_weight,
            'charge_weight': self.charge_weight,
            'pcs': self.pcs,
            'uom_id': self.uom_id.id if self.uom_id else False,
            'other': self.other,
            # Lines
            'flight_routing_ids': flight_lines,
            'dimension_ids': dimension_lines,
        }
        hawb = self.env['freight.air.hawb'].create(hawb_vals)
        return {
            'name': _('Air Jobsheet (HAWB)'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.air.hawb',
            'res_id': hawb.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_hawbs(self):
        self.ensure_one()
        hawbs = self.hawb_ids
        return {
            'name': _('Air Jobsheets (HAWBs)'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.air.hawb',
            'view_mode': 'form' if len(hawbs) == 1 else 'list,form',
            'domain': [('id', 'in', hawbs.ids)],
            'res_id': hawbs.id if len(hawbs) == 1 else False,
            'context': dict(self.env.context, default_booking_id=self.id),
        }

    action_create_jobsheet = action_create_hawb
    action_view_jobsheets = action_view_hawbs


