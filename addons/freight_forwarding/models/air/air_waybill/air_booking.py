from odoo import api, models, fields

class AirBooking(models.Model):
    _name = 'freight.air.booking'
    _description = 'Air Booking'
    _rec_name = 'booking_no'

    _sql_constraints = [
        ('booking_no_unique', 'UNIQUE(booking_no)', 'Booking No. must be unique!'),
        ('job_no_unique', 'UNIQUE(job_no)', 'Job No. must be unique!'),
    ]

    booking_no = fields.Char(string='Booking No', required=True, copy=False, readonly=True, default=lambda self: 'New')
    booking_type = fields.Selection(
        [('export', 'Export'),
        ('import', 'Import')],
        string='Booking Type',
        required=True
    )

    #Left Side
    job_no = fields.Char(string='Job No', required=True, copy=False, readonly=True, default=lambda self: 'New')
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        domain=[('category_id.name', '=', 'Customer')],
        required=True
    )
    nomination_cargo = fields.Boolean(string="Nomination Cargo")
    booking_from_id = fields.Many2one(
        'res.partner',
        string='Booking From'
    )
    email = fields.Char(related='booking_from_id.email', string='Email', readonly=True)
    phone = fields.Char(related='booking_from_id.phone', string='Phone', readonly=True)
    customer_ref = fields.Char(related='booking_from_id.ref', string='Customer Ref', readonly=True)
    shipper_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Shipper')]",
        string='Shipper'
    )
    consignee_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Consignee')]",
        string='Consignee'
    )

    #Right Side
    coloader_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Co-loader')]",
        string='Co-loader'
    )

    overseas_agent_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Overseas Agent')]",
        string='Overseas Agent'
    )

    overseas_agent_id_ref = fields.Char(
        related='overseas_agent_id.ref', 
        string='Overseas Agent Ref', 
        readonly=True
    )

    departure_airport_id = fields.Many2one(
        'freight.airport',
        string='Departure Airport'
    )

    destination_airport_id = fields.Many2one(
        'freight.airport',
        string='Destination Airport'
    )

    origin_country_id = fields.Many2one(
        'res.country',
        string='Origin Country'
    )

    wt_val = fields.Selection(
        [('p', 'P'),
        ('c', 'C')],
        string='WT/VAL',
    )

    other = fields.Selection(
        [('p', 'P'),
        ('c', 'C')],
        string='Other',
    )

    # Flight Details
    first_flight_to = fields.Many2one(
        'freight.airport',
        string='First Flight To'
    )
    first_flight_by = fields.Many2one(
        'freight.airline',
        string='By'
    )
    first_flight_on = fields.Date(string='On')

    second_flight_to = fields.Many2one(
        'freight.airport',
        string='Second Flight To'
    )
    second_flight_by = fields.Many2one(
        'freight.airline',
        string='By'
    )
    second_flight_on = fields.Date(string='On')

    third_flight_to = fields.Many2one(
        'freight.airport',
        string='Third Flight To'
    )
    third_flight_by = fields.Many2one(
        'freight.airline',
        string='By'
    )
    third_flight_on = fields.Date(string='On')

    fourth_flight_to = fields.Many2one(
        'freight.airport',
        string='Fourth Flight To'
    )
    fourth_flight_by = fields.Many2one(
        'freight.airline',
        string='By'
    )
    fourth_flight_on = fields.Date(string='On')


    service_level = fields.Selection(
        [('p1', 'P1'),
        ('p2', 'P2'),
        ('p3', 'P3'),
        ('p4', 'P4')],
        string='Service Level'
    )
    pcs = fields.Integer(string='PCS/RCP')
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM'
    )

    gross_weight = fields.Float(string='Gross Weight')
    charge_weight = fields.Float(string='Charge Weight')
    commodity_id = fields.Many2one(
        'freight.commodity',
        string='Commodity'
    )

    note = fields.Text(string='Note')

    # NOTEBOOK

    # Dimension
    loose_quantity = fields.Integer(string='Loose Quantity')
    pcs = fields.Integer(string='PCS')
    # duplikat uom

    length = fields.Float(string='Length')
    width = fields.Float(string='Width')
    height = fields.Float(string='Height')
    dimension = fields.Float(string='Dimension')


    # Pickup Info
    pickup_no = fields.Char(string='Pickup No.')
    pickup_date = fields.Date(string='Pickup Date')
    transport_company_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Transport Company')]",
        string='Transport Company'
    )

    collect_from_id = fields.Many2one(
        'res.partner',
        string='Collect From'
    )
    collect_from_address = fields.Char(
        related='collect_from_id.contact_address', 
        string='Address', 
        readonly=True
    )
    collect_from_phone = fields.Char(
        related='collect_from_id.phone', 
        string='Phone', 
        readonly=True
    )

    delivery_from_id = fields.Many2one(
        'res.partner',
        string='Delivery From'
    )
    delivery_from_address = fields.Char(
        related='delivery_from_id.contact_address',
        string='Address',
        readonly=True
    )
    delivery_from_phone = fields.Char(
        related='delivery_from_id.phone',
        string='Phone',
        readonly=True
    )

    status = fields.Selection(
        [('progress', 'Progress'),
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
        ('cancelled', 'Cancelled')],
        string='Status',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('booking_no', 'New') == 'New':
                vals['booking_no'] = self.env['ir.sequence'].next_by_code('freight.air.booking.no') or 'New'
            if vals.get('job_no', 'New') == 'New':
                vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.booking.job.no') or 'New'
        return super().create(vals_list)