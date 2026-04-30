from odoo import api, fields, models


class AirMAWB(models.Model):
    _name = 'freight.air.mawb'
    _description = 'Air MAWB'
    _rec_name = 'mawb_no'

    _sql_constraints = [
        ('mawb_no_unique', 'UNIQUE(mawb_no)', 'MAWB No. must be unique!'),
        ('job_no_unique', 'UNIQUE(job_no)', 'Job No. must be unique!'),
    ]

    mawb_no = fields.Char(
        string='MAWB No',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'New'
    )
    quotation_id = fields.Many2one(
        'sale.order',
        string='Quotation Number',
        required=True,
        domain="[('transportation_method', '=', 'air')]"
    )

    booking_id = fields.Many2one(
        'freight.air.booking',
        string='Booking No.',
        required=True,
    )
    job_no = fields.Char(
        string='Job No.',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'New'
    )
    job_date = fields.Date(
        string='Job Date',
        default=fields.Date.context_today
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer Name',
        domain="[('category_id.name', '=', 'Customer')]",
        readonly=True
    )
    customer_ref = fields.Char(
        related='customer_id.ref',
        string='Customer Ref',
        readonly=True
    )
    credit_term_id = fields.Many2one(
        'account.payment.term',
        string='Credit Term',
    )
    nomination_cargo = fields.Boolean(
        related='booking_id.nomination_cargo',
        string='Nomination Cargo',
        readonly=True
    )
    shipper_id = fields.Many2one(
        'res.partner',
        string='Shipper Name',
        domain="[('category_id.name', '=', 'Shipper')]",
    )
    shipper_address = fields.Char(
        related='shipper_id.contact_address',
        string='Shipper Address',
        readonly=True
    )
    consignee_id = fields.Many2one(
        'res.partner',
        string='Consignee Name',
        domain="[('category_id.name', '=', 'Consignee')]",
    )
    consignee_address = fields.Char(
        related='consignee_id.contact_address',
        string='Consignee Address',
        readonly=True
    )
    consignee_account_no = fields.Char(
        related='consignee_id.bank_ids.acc_number',
        string='Consignee Account No.',
        readonly=True
    )
    notify_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Notify Party')]",
        string='Notify Name'
    )
    notify_address = fields.Char(
        related='notify_id.contact_address',
        string='Notify Address',
        readonly=True
    )
    overseas_agent_id = fields.Many2one(
        'res.partner',
        string='Overseas Agent Name',
        domain="[('category_id.name', '=', 'Overseas Agent')]",
    )
    agent_id = fields.Many2one(
        'res.partner',
        string='Agent Name'
    )
    iata_account_no = fields.Char(string='IATA Account No.')
    awb_file = fields.Binary(
        string='Upload AWB',
        attachment=True
    )
    awb_filename = fields.Char(string='AWB Filename')
    note = fields.Text(string='Note')

    # Extra Info
    extra_info_ids = fields.One2many(
        'freight.air.extra.info',
        'mawb_id',
        string='Extra Info'
    )

    # Shipment Info
    departure_airport_id = fields.Many2one(
        'freight.airport',
        string='Departure Airport'
    )
    first_carrier_to_id = fields.Many2one(
        'freight.airport',
        string='1st Carrier To'
    )
    first_carrier_by_id = fields.Many2one(
        'freight.airline',
        string='By'
    )
    first_carrier_date = fields.Date(string='Date')
    first_carrier_eta = fields.Date(string='ETA1')

    second_carrier_to_id = fields.Many2one(
        'freight.airport',
        string='2nd Carrier To'
    )
    second_carrier_by_id = fields.Many2one(
        'freight.airline',
        string='By'
    )
    second_carrier_date = fields.Date(string='Date')
    second_carrier_eta = fields.Date(string='ETA2')

    third_carrier_to_id = fields.Many2one(
        'freight.airport',
        string='3rd Carrier To'
    )
    third_carrier_by_id = fields.Many2one(
        'freight.airline',
        string='By'
    )
    third_carrier_date = fields.Date(string='Date')
    third_carrier_eta = fields.Date(string='ETA3')

    fourth_carrier_to_id = fields.Many2one(
        'freight.airport',
        string='4th Carrier To'
    )
    fourth_carrier_by_id = fields.Many2one(
        'freight.airline',
        string='By'
    )
    fourth_carrier_date = fields.Date(string='Date')
    fourth_carrier_eta = fields.Date(string='ETA4')

    destination_airport_id = fields.Many2one(
        'freight.airport',
        string='Destination Airport'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )
    weight_value = fields.Selection(
        [('prepaid', 'Prepaid'), ('collect', 'Collect')],
        string='Weight Value'
    )
    other_value = fields.Selection(
        [('prepaid', 'Prepaid'), ('collect', 'Collect')],
        string='Other'
    )
    billing_party_id = fields.Many2one(
        'res.partner',
        string='Billing Party',
        domain="[('category_id.name', '=', 'Billing Party')]"
    )
    other_billing_party_id = fields.Many2one(
        'res.partner',
        domain="[('category_id.name', '=', 'Billing Party')]",
        string='Billing Party'
    )
    currency_code = fields.Char(
        related='currency_id.name',
        string='Currency Code',
        readonly=True
    )
    currency_rate = fields.Float(string='Currency Rate', default=1.0)

    declared_value_for_carriage = fields.Char(string='Declared Value For Carriage')
    customs_currency_id = fields.Many2one(
        'res.currency',
        string='Customs'
    )
    custom_local_amount = fields.Monetary(
        string='Custom Local Amount',
        currency_field='customs_currency_id'
    )
    ship_mode = fields.Selection(
        [('routing_order', 'Routing Order'), 
         ('free_hans', 'Free Hans'),
         ('transit', 'Transit')],
        string='Ship Mode'
    )
    insurance_currency_id = fields.Many2one(
        'res.currency',
        string='Insurance Currency'
    )
    insurance_amount = fields.Monetary(
        string='Insurance Amount',
        currency_field='insurance_currency_id'
    )
    insurance_local_amount = fields.Monetary(
        string='Insurance Local Amount',
        currency_field='insurance_currency_id'
    )
    dg_cargo = fields.Boolean(string='DG Cargo')
    handling_information = fields.Many2one(
        'freight.air.handling.information',
        string='Handling Information'
    )
    accounting_information = fields.Text(string='Accounting Information')
    coloader_id = fields.Many2one(
        'res.partner',
        string='Co-Loader',
        domain="[('category_id.name', '=', 'Co-loader')]"
    )
    permit_no = fields.Char(string='Permit No')
    print_dimension = fields.Boolean(string='Print Dimension')
    delivery_type_id = fields.Many2one(
        'freight.delivery.type',
        string='Delivery Type'
    )

    # Custom Permit
    custom_permit_ids = fields.One2many(
        'freight.air.custom.permit',
        'mawb_id',
        string='Custom Permit'
    )

    # Package Details
    package_details_ids = fields.One2many(
        'freight.air.mawb.package.details',
        'mawb_id',
        string='Package Details'
    )

    # Document List
    document_list_ids = fields.One2many(
        'freight.air.document.list',
        'mawb_id',
        string='Document List'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('mawb_no', 'New') == 'New':
                vals['mawb_no'] = self.env['ir.sequence'].next_by_code('freight.air.mawb') or 'New'
            if vals.get('job_no', 'New') == 'New':
                vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.mawb.job') or 'New'
        return super().create(vals_list)
