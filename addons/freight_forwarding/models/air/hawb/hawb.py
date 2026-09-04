from odoo import models, fields, api, _

class FreightAirHawb(models.Model):
    _name = 'freight.air.hawb'
    _description = 'Air Freight Jobsheet (HAWB)'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'freight.air.awb.info.mixin',
        'freight.air.shipment.info.mixin',
        'freight.air.cargo.info.mixin'
    ]
    _order = 'id desc'
    _rec_name = 'job_no'

    job_no = fields.Char(string='Job No.', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    job_date = fields.Date(string='Job Date', default=fields.Date.context_today, required=True, tracking=True)
    hawb_no = fields.Char(string='House AWB No.', tracking=True)
    smawb_no = fields.Char(string='SMawb No.', tracking=True)
    mawb_no = fields.Char(string='Mawb No.', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    
    booking_id = fields.Many2one('freight.air.booking', string='Booking No.', tracking=True)
    freight_type = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export')
    ], string='Type', required=True, tracking=True, default='export')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Customer Code', required=True, tracking=True)
    customer_ref = fields.Char(string='Cust Ref')
    is_nomination = fields.Boolean(string='Nomination Cargo')
    nomination_remark = fields.Char(string='Nomination Remark')
    term_payment = fields.Many2one('account.payment.term', string='Credit Term')
    awb_prefix = fields.Char(string='Awb Prefix')
    
    salesman_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=False)

    # -------------------------------------------------------------
    # TAB 1: Awb Info - Address & Accounts (Addresses inherited from FreightAirAwbInfoMixin)
    # -------------------------------------------------------------
    shipper_account_no = fields.Char(string='Shipper Account No.')
    consignee_account_no = fields.Char(string='Consignee Account No.')
    notify_is_bank = fields.Boolean(string='Bank')

    iata_code = fields.Char(string='IATA Code')
    agent_account_no = fields.Char(string='Agent Account No.')
    note = fields.Text(string='Note')

    # -------------------------------------------------------------
    # TAB 2: Shipment Info
    # -------------------------------------------------------------
    destination_date = fields.Date(string='Destination Date')
    flight_routing_ids = fields.One2many('freight.air.hawb.flight.routing', 'hawb_id', string='Flight Routings')

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

    handling_information_id = fields.Many2one('freight.air.handling.information', string='Handling Information')
    handling_information = fields.Text(string='Handling Information')
    accounting_information = fields.Text(string='Accounting Information')
    permit_no = fields.Char(string='Permit No.')
    print_dimension = fields.Boolean(string='Print Dimension', default=True)

    # -------------------------------------------------------------
    # TAB 3: Dimension
    # -------------------------------------------------------------
    @api.model
    def _default_ratio_uom(self):
        return self.env.ref('uom.product_uom_cm', raise_if_not_found=False) or self.env['uom.uom'].search([('category_id.name', 'ilike', 'Length'), ('name', 'ilike', 'cm')], limit=1)

    @api.model
    def _default_weight_uom(self):
        return self.env.ref('uom.product_uom_kgm', raise_if_not_found=False) or self.env['uom.uom'].search([('category_id.name', 'ilike', 'Weight'), ('name', 'ilike', 'kg')], limit=1)

    vol_weight_ratio = fields.Float(string='Volume/Weight Ratio', default=6000.0)
    ratio_uom_id = fields.Many2one('uom.uom', string='Ratio Unit', domain="[('category_id.name', 'ilike', 'Length')]", default=_default_ratio_uom)
    is_round_up = fields.Boolean(string='Round Up', default=True)
    weight_uom_id = fields.Many2one('uom.uom', string='Kg/Lb', domain="[('category_id.name', 'ilike', 'Weight')]", default=_default_weight_uom)
    dimension_ids = fields.One2many('freight.air.hawb.dimension', 'hawb_id', string='Dimensions')

    # -------------------------------------------------------------
    # Document List & Job Costing
    # -------------------------------------------------------------
    invoice_ids = fields.One2many('freight.air.hawb.invoice', 'hawb_id', string='Invoice')
    debit_note_ids = fields.One2many('freight.air.hawb.debit.note', 'hawb_id', string='Debit Note')
    credit_note_ids = fields.One2many('freight.air.hawb.credit.note', 'hawb_id', string='Credit Note')
    provision_cost_ids = fields.One2many('freight.air.hawb.provision.cost', 'hawb_id', string='Provision Cost')
    vendor_invoice_ids = fields.One2many('freight.air.hawb.vendor.invoice', 'hawb_id', string='Vendor Invoice')
    vendor_debit_note_ids = fields.One2many('freight.air.hawb.vendor.debit.note', 'hawb_id', string='Vendor Debit Note')
    vendor_credit_note_ids = fields.One2many('freight.air.hawb.vendor.credit.note', 'hawb_id', string='Vendor Credit Note')
    cash_purchase_ids = fields.One2many('freight.air.hawb.cash.purchase', 'hawb_id', string='Cash Purchase')

    sale_order_ids = fields.Many2many('sale.order', string='Sales Orders')
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders')
    sales_order_count = fields.Integer(string='Sales Order Count', compute='_compute_sales_order_count')
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_purchase_order_count')

    @api.depends('sale_order_ids')
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    def action_view_sales_orders(self):
        self.ensure_one()
        orders = self.sale_order_ids
        if not orders:
            return False
        return {
            'name': _('Sales Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form' if len(orders) == 1 else 'list,form',
            'domain': [('id', 'in', orders.ids)],
            'res_id': orders.id if len(orders) == 1 else False,
            'context': dict(
                self.env.context,
                default_air_hawb_id=self.id,
                default_is_freight_quotation=True,
                default_freight_business_type='air',
                form_view_ref='freight_forwarding.view_air_quotation_form',
            ),
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        orders = self.purchase_order_ids
        if not orders:
            return False
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form' if len(orders) == 1 else 'list,form',
            'domain': [('id', 'in', orders.ids)],
            'res_id': orders.id if len(orders) == 1 else False,
            'context': dict(
                self.env.context,
                default_air_hawb_id=self.id,
            ),
        }

    @api.depends('dimension_ids.volume', 'dimension_ids.qty', 'vol_weight_ratio', 'is_round_up')
    def _compute_cargo_totals(self):
        import math
        for rec in self:
            total_vol = sum(d.volume for d in rec.dimension_ids)
            total_pcs = sum(d.qty for d in rec.dimension_ids)
            rec.total_pcs = total_pcs
            rec.total_dimension = total_vol
            rec.total_m3 = total_vol / 1000000.0 if total_vol else 0.0
            ratio = rec.vol_weight_ratio or 6000.0
            calc_vol_wt = total_vol / ratio if total_vol else 0.0
            if rec.is_round_up:
                calc_vol_wt = math.ceil(calc_vol_wt)
            rec.volumetric_weight = calc_vol_wt
            rec.total_vol_weight = calc_vol_wt

    @api.onchange('handling_information_id')
    def _onchange_handling_information_id(self):
        if self.handling_information_id:
            self.handling_information = self.handling_information_id.description or self.handling_information_id.name

    def action_same_as_consignee(self):
        self.ensure_one()
        if self.consignee_id:
            self.notify_party_id = self.consignee_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('job_no', _('New')) == _('New'):
                freight_type = vals.get('freight_type', 'export')
                if freight_type == 'export':
                    vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.hawb.job_no.exp') or _('New')
                else:
                    vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.hawb.job_no.imp') or _('New')
        
        plan = self.env["account.analytic.plan"].search([], limit=1)
        if not plan:
            plan = self.env["account.analytic.plan"].create({"name": "Default"})
        records = super(FreightAirHawb, self).create(vals_list)
        for res in records:
            if not res.analytic_account_id:
                analytic_account = self.env['account.analytic.account'].create({
                    'name': res.job_no,
                    'plan_id': plan.id,
                    'company_id': res.company_id.id if res.company_id else self.env.company.id,
                    'partner_id': res.partner_id.id if res.partner_id else False,
                })
                res.analytic_account_id = analytic_account.id
        records._sync_analytic_to_related_docs()
        return records

    def write(self, vals):
        res = super(FreightAirHawb, self).write(vals)
        self._sync_analytic_to_related_docs()
        return res

    def _sync_analytic_to_related_docs(self):
        import json
        for rec in self:
            if not rec.analytic_account_id:
                continue

            distribution = {str(rec.analytic_account_id.id): 100.0}

            # 1. Sync to Sales Orders & Lines
            if rec.sale_order_ids:
                for so in rec.sale_order_ids:
                    if hasattr(so, "air_hawb_id") and not so.air_hawb_id:
                        so.air_hawb_id = rec.id
                    if hasattr(so, "analytic_account_id") and not so.analytic_account_id:
                        so.analytic_account_id = rec.analytic_account_id.id
                    for line in so.order_line:
                        if not line.analytic_distribution:
                            self.env.cr.execute(
                                "UPDATE sale_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(["analytic_distribution"])

            # 2. Sync to Purchase Orders & Lines
            if rec.purchase_order_ids:
                for po in rec.purchase_order_ids:
                    if hasattr(po, "air_hawb_id") and not po.air_hawb_id:
                        po.air_hawb_id = rec.id
                    for line in po.order_line:
                        if not line.analytic_distribution:
                            self.env.cr.execute(
                                "UPDATE purchase_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(["analytic_distribution"])

            # 3. Sync to Invoices / Vendor Bills
            moves = self.env["account.move"]
            if rec.purchase_order_ids:
                moves |= rec.purchase_order_ids.mapped("invoice_ids")
            if rec.sale_order_ids:
                moves |= rec.sale_order_ids.mapped("invoice_ids")
            moves |= self.env["account.move"].search([("air_hawb_id", "=", rec.id)])

            # Document list references
            doc_fields = [
                "vendor_invoice_ids", "invoice_ids", "debit_note_ids", "credit_note_ids",
                "vendor_debit_note_ids", "vendor_credit_note_ids", "cash_purchase_ids", "provision_cost_ids"
            ]
            ref_attr_names = [
                "vendor_invoice_reference", "invoice_reference", "debit_note_reference", "credit_note_reference",
                "vendor_debit_note_reference", "vendor_credit_note_reference", "cash_purchase_reference", "provision_cost_reference"
            ]
            for doc_field in doc_fields:
                if hasattr(rec, doc_field) and getattr(rec, doc_field):
                    for doc_item in getattr(rec, doc_field):
                        for ref_name in ref_attr_names:
                            if hasattr(doc_item, ref_name):
                                val = getattr(doc_item, ref_name)
                                if val:
                                    moves |= val

            for move in moves:
                if hasattr(move, "air_hawb_id") and not move.air_hawb_id:
                    move.air_hawb_id = rec.id
                for line in move.invoice_line_ids:
                    if not line.analytic_distribution and line.display_type not in ("line_section", "line_note"):
                        self.env.cr.execute(
                            "UPDATE account_move_line SET analytic_distribution = %s WHERE id = %s",
                            (json.dumps(distribution), line.id)
                        )
                        line.invalidate_recordset(["analytic_distribution"])

    def action_active(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})
