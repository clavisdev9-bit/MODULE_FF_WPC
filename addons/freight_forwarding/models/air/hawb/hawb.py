from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FreightAirHawb(models.Model):
    _name = 'freight.air.job'
    _description = 'Air Freight Job (Direct/Master/House AWB)'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'freight.air.awb.info.mixin',
        'freight.air.shipment.info.mixin',
        'freight.air.cargo.info.mixin',
        'freight.commercial.group.mixin',
        'freight.job.type.resolver.mixin',
    ]
    _order = 'id desc'
    _rec_name = 'job_no'
    _job_type_business_type = 'air'
    _sql_constraints = [
        ('job_no_uniq', 'unique(job_no)', 'Job No. harus unik.'),
        ('document_id_uniq', 'unique(document_id)',
         'AWB ini sudah dipakai Job lain.'),
    ]

    job_no = fields.Char(string='Job No.', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    # FF-75: discriminator record level dipakai lewat shipment_type
    # (direct/house/master) yang sudah ada -- lihat freight.air.shipment.info.mixin.
    # Direct TIDAK ikut hierarchy Master/House (di luar scope FF-75).
    master_job_id = fields.Many2one(
        'freight.air.job',
        string='Master Job',
        domain="[('shipment_type', '=', 'master'), ('id', '!=', id)]",
        tracking=True,
        ondelete='restrict',
        help='Master Job tempat House AWB ini bergabung. WAJIB terisi untuk '
             'House (House tidak boleh berdiri sendiri). Kosong untuk Master '
             'dan untuk Direct.',
    )
    house_job_ids = fields.One2many(
        'freight.air.job',
        'master_job_id',
        string='House Jobs',
    )
    job_date = fields.Date(string='Job Date', default=fields.Date.context_today, tracking=True)
    smawb_no = fields.Char(string='SMawb No.', tracking=True)
    # FF-76: hawb_no/mawb_no/effective_mawb_no/direct_awb_no (raw Char per
    # shipment_type) dihapus -- diganti satu relation canonical document_id
    # (ke registry shared freight.transport.document). Canonical meaning
    # tergantung shipment_type: Master = own Master AWB, House = own House
    # AWB, Direct = own Direct AWB. Label UI dibedakan lewat form view
    # (string override), bukan field teknis terpisah.
    document_id = fields.Many2one(
        'freight.transport.document',
        string='AWB No.',
        domain="[('transport_mode', '=', 'air')]",
        tracking=True,
    )
    # FF-76: House TIDAK menyimpan duplicate MAWB Char -- MAWB House
    # berasal dari master_job_id.document_id (non-canonical, readonly
    # helper, hanya supaya bisa dipakai sebagai field form/search biasa).
    master_document_id = fields.Many2one(
        'freight.transport.document',
        string='MAWB No.',
        compute='_compute_master_document_id',
        store=True,
    )
    # FF-76: Booking reference House juga berasal dari Master -- helper
    # readonly/searchable, BUKAN duplicate Booking No. Char.
    effective_booking_id = fields.Many2one(
        'freight.air.booking',
        string='Booking',
        compute='_compute_effective_booking_id',
        store=True,
    )
    known_shipper_flag = fields.Char(string='Know Shipper', size=15, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    
    booking_id = fields.Many2one('freight.air.booking', string='Booking No.', tracking=True)
    # FF-73 hardening: TIDAK ada default -- lihat komentar setara di
    # freight.air.booking.freight_type. Sebelumnya default='export' di sini
    # menyebabkan semantic inconsistency: create({}) tanpa freight_type
    # (vals kosong saat create() override di bawah membaca job_no sequence)
    # tetap menghasilkan job_no NETRAL (JKT-AJOB/...) tapi freight_type akhir
    # jadi 'export' (dari default field, diterapkan ORM SETELAH override ini
    # membaca vals) -- job_no dan freight_type jadi tidak konsisten.
    freight_type = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export')
    ], string='Type', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Customer Code', tracking=True)
    customer_ref = fields.Char(string='Cust Ref')
    is_nomination = fields.Boolean(string='Nomination Cargo')
    nomination_remark = fields.Char(string='Nomination Remark')
    term_payment = fields.Many2one('account.payment.term', string='Credit Term')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=False)

    # -------------------------------------------------------------
    # TAB 1: Awb Info - Address & Accounts (Addresses inherited from FreightAirAwbInfoMixin)
    # -------------------------------------------------------------
    shipper_account_no = fields.Char(string='Shipper Account No.')
    consignee_account_no = fields.Char(string='Consignee Account No.')
    consignee_postal_code = fields.Char(related='consignee_id.zip', string='Postal Code', readonly=True)
    notify_is_bank = fields.Boolean(string='Bank')

    iata_code = fields.Char(string='IATA Code')
    agent_account_no = fields.Char(string='Agent Account No.')
    note = fields.Text(string='Note')

    # -------------------------------------------------------------
    # AWB Info (Air Import) - Clearance/Transshipment, Appointed Agent, Contacts, Warehouse
    # -------------------------------------------------------------
    clearance = fields.Selection([
        ('house', 'House'),
        ('others', 'Others'),
    ], string='Clearance', tracking=True)
    is_transhipment = fields.Boolean(string='Transhipment', tracking=True)
    origin_mawb_no = fields.Char(string='Origin MAWB No.', tracking=True)

    appointed_agent_id = fields.Many2one('res.partner', string='Appointed Agent', tracking=True)

    contact_person_id = fields.Many2one(
        'res.partner', string='Contact Person',
    )
    consignee_contact_phone = fields.Char(related='contact_person_id.phone', string='Telephone')

    agent_contact_id = fields.Many2one(
        'res.partner', string='Contact Person',
        domain="[('parent_id', '=', appointed_agent_id)]",
    )
    agent_contact_phone = fields.Char(related='agent_contact_id.phone', string='Telephone')

    warehouse_id = fields.Many2one(
        'res.partner', string='Warehouse', tracking=True,
        domain="[('category_id.name', '=', 'Warehouse')]",
    )

    # -------------------------------------------------------------
    # TAB 2: Shipment Info (fields shared with Booking live in
    # freight.air.shipment.info.mixin; only the hawb-specific flight
    # routing lines stay here, since they point at a hawb-only child model)
    # -------------------------------------------------------------
    flight_routing_ids = fields.One2many('freight.air.job.flight.routing', 'job_id', string='Flight Routings')

    # -------------------------------------------------------------
    # Delivery Info (Air Import) - pickup/delivery context only, not Warehouse
    # -------------------------------------------------------------
    transport_company_id = fields.Many2one(
        'res.partner', string='Transport Company', tracking=True,
        domain="[('category_id.name', '=', 'Transport Company')]",
    )
    transport_company_address = fields.Char(related='transport_company_id.contact_address', string='Address', readonly=True)

    pickup_datetime = fields.Datetime(string='Pickup Date/Time')
    collect_from_id = fields.Many2one('res.partner', string='Collect From')
    collect_from_address = fields.Char(related='collect_from_id.contact_address', string='Collect From Address', readonly=True)

    delivery_datetime = fields.Datetime(string='Delivery Date/Time')
    deliver_to_id = fields.Many2one('res.partner', string='Deliver To')
    deliver_to_address = fields.Char(related='deliver_to_id.contact_address', string='Deliver To Address', readonly=True)

    delivery_instruction = fields.Text(string='Delivery Instruction')

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
    dimension_ids = fields.One2many('freight.air.job.dimension', 'job_id', string='Dimensions')

    # -------------------------------------------------------------
    # Document List & Job Costing
    # -------------------------------------------------------------
    invoice_ids = fields.One2many('freight.air.job.invoice', 'job_id', string='Invoice')
    debit_note_ids = fields.One2many('freight.air.job.debit.note', 'job_id', string='Debit Note')
    credit_note_ids = fields.One2many('freight.air.job.credit.note', 'job_id', string='Credit Note')
    provision_cost_ids = fields.One2many('freight.air.job.provision.cost', 'job_id', string='Provision Cost')
    vendor_invoice_ids = fields.One2many('freight.air.job.vendor.invoice', 'job_id', string='Vendor Invoice')
    vendor_debit_note_ids = fields.One2many('freight.air.job.vendor.debit.note', 'job_id', string='Vendor Debit Note')
    vendor_credit_note_ids = fields.One2many('freight.air.job.vendor.credit.note', 'job_id', string='Vendor Credit Note')
    cash_purchase_ids = fields.One2many('freight.air.job.cash.purchase', 'job_id', string='Cash Purchase')

    sale_order_ids = fields.Many2many('sale.order', string='Sales Orders')
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders')
    sales_order_count = fields.Integer(string='Sales Order Count', compute='_compute_sales_order_count')
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_purchase_order_count')

    booking_count = fields.Integer(
        string='Booking Count',
        compute='_compute_booking_count',
    )

    @api.depends('booking_id', 'master_job_id.booking_id')
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = 1 if rec._get_effective_booking() else 0

    @api.depends('sale_order_ids')
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    def _get_source_quotation(self):
        """FF-75 semantic consistency: Master BUKAN commercial owner
        Quotation manapun -- TIDAK boleh resolve source lewat Booking.
        House selalu punya source_quotation_id sendiri (diisi langsung saat
        dibuat), jadi tidak butuh fallback apa pun.

        Direct (out of scope FF-75, behavior existing dipertahankan) tetap
        boleh fallback ke Booking: Direct adalah standalone Job yang bisa
        dibuat lewat Booking tanpa source_quotation_id sendiri (lihat
        action_create_job Booking) -- root-nya diambil dari
        Booking._get_source_quotation() persis seperti sebelum FF-75."""
        self.ensure_one()
        if self.source_quotation_id:
            return self.source_quotation_id
        if self.shipment_type == 'direct' and self.booking_id:
            return self.booking_id._get_source_quotation()
        return False

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    @api.constrains('shipment_type', 'master_job_id')
    def _check_master_house_hierarchy(self):
        for rec in self:
            if rec.shipment_type in ('master', 'direct') and rec.master_job_id:
                raise ValidationError(
                    "Master Job dan Direct AWB tidak boleh memiliki master_job_id (master_job_id harus kosong)."
                )
            if rec.shipment_type == 'house' and not rec.master_job_id:
                raise ValidationError("House AWB wajib menunjuk ke Master Job (master_job_id tidak boleh kosong).")
            if rec.master_job_id:
                if rec.master_job_id.id == rec.id:
                    raise ValidationError("Job tidak boleh menjadi Master Job untuk dirinya sendiri.")
                if rec.master_job_id.shipment_type != 'master':
                    raise ValidationError("master_job_id harus menunjuk ke Job dengan Shipment Type 'Master'.")

    @api.constrains('shipment_type')
    def _check_master_cannot_become_house_or_direct(self):
        """FF-75 follow-up: proteksi dari sisi parent -- Master yang sudah
        punya House tidak boleh diubah jadi House/Direct lewat write/RPC."""
        for rec in self:
            if rec.shipment_type in ('house', 'direct') and rec.house_job_ids:
                raise ValidationError(
                    "Job (%s) tidak bisa diubah dari Master menjadi %s karena masih "
                    "memiliki House Job (%s)." % (
                        rec.job_no, rec.shipment_type, ", ".join(rec.house_job_ids.mapped("job_no"))
                    )
                )

    @api.model
    def _find_commercial_group_house(self, quotation):
        """Manual UAT follow-up FF-75: House Air lain (shipment_type='house')
        yang source_quotation_id-nya berada di commercial group (root +
        seluruh currency variant) yang sama dengan `quotation`. Mirror
        freight.sea.job._find_commercial_group_house -- lihat komentar
        lengkap di sana. Direct AWB TIDAK ikut rule ini sama sekali."""
        if not quotation:
            return self.browse()
        root = quotation.original_quotation_id or quotation
        group_ids = (root | root.variant_ids).ids
        return self.search([
            ('shipment_type', '=', 'house'),
            ('source_quotation_id', 'in', group_ids),
        ])

    @api.constrains('shipment_type', 'source_quotation_id')
    def _check_single_house_per_commercial_group(self):
        """Manual UAT follow-up FF-75: 1 commercial quotation group (root +
        seluruh currency variant) maksimal punya 1 House Air. Berlaku murni
        untuk House -- Master dan Direct AWB tidak ikut rule ini. Ditangkap
        lewat create() MAUPUN write()."""
        for rec in self:
            if rec.shipment_type != 'house' or not rec.source_quotation_id:
                continue
            duplicates = rec._find_commercial_group_house(rec.source_quotation_id) - rec
            if duplicates:
                root = rec.source_quotation_id.original_quotation_id or rec.source_quotation_id
                raise ValidationError(
                    "Quotation %s (beserta seluruh currency variant-nya) sudah "
                    "memiliki House Job (%s) -- satu Quotation hanya boleh "
                    "menghasilkan maksimal 1 House Job." % (root.name, duplicates[0].job_no)
                )

    @api.constrains('analytic_account_id', 'master_job_id')
    def _check_house_analytic_matches_master(self):
        """FF-75: invariant keras -- House TIDAK BOLEH punya analytic account
        yang beda dari Master-nya, lewat jalur apa pun (create/write/RPC)."""
        for rec in self:
            if rec.master_job_id and rec.analytic_account_id != rec.master_job_id.analytic_account_id:
                raise ValidationError(
                    "House (%s) tidak boleh memiliki Analytic Account independen -- "
                    "harus sama dengan Master Job (%s)." % (rec.job_no, rec.master_job_id.job_no)
                )

    @api.depends('shipment_type', 'master_job_id.document_id')
    def _compute_master_document_id(self):
        for rec in self:
            rec.master_document_id = rec.master_job_id.document_id if rec.master_job_id else False

    @api.depends('shipment_type', 'booking_id', 'master_job_id.booking_id')
    def _compute_effective_booking_id(self):
        """FF-76: House -> master_job_id.booking_id; Master/Direct -> own
        booking_id. Berbeda dari _get_effective_booking() (fallback chain
        generik yang sudah ada untuk tombol/counter) -- field ini murni
        untuk kebutuhan search/list canonical berdasarkan shipment_type."""
        for rec in self:
            if rec.shipment_type == 'house' and rec.master_job_id:
                rec.effective_booking_id = rec.master_job_id.booking_id
            else:
                rec.effective_booking_id = rec.booking_id

    @api.constrains('document_id')
    def _check_awb_master_chain(self):
        """FF-76: AWB availability/ownership rule terpusat di sini.
        - SQL unique constraint (document_id_uniq) sudah menolak 2 Job
          mana pun (Master/House/Direct apa saja) berbagi document yang sama.
        - Satu-satunya exception LEGAL: Master hasil action_create_job dari
          Booking yang SAMA memakai document yang sudah dipakai Booking
          tersebut (chain Booking->Master).
        - Kalau document sudah pernah dipakai (is_used) oleh chain lain
          (Job lain, atau Booking yang bukan booking_id milik rec), tolak --
          one-time semantic, bukan cuma cek relation kosong."""
        for rec in self:
            awb = rec.document_id
            if not awb:
                continue
            if awb.transport_mode != 'air':
                raise ValidationError(
                    "AWB %s bertipe '%s' -- Air Job hanya boleh memakai "
                    "AWB Type Air." % (awb.document_no, awb.transport_mode)
                )
            if not awb.is_used:
                continue
            legal = awb.used_air_job_id == rec or (
                rec.shipment_type == 'master'
                and awb.used_air_booking_id
                and rec.booking_id == awb.used_air_booking_id
            )
            if not legal:
                raise ValidationError(
                    "AWB %s sudah pernah digunakan dan tidak dapat dipakai "
                    "ulang oleh Job ini." % awb.document_no
                )

    @api.constrains('document_id', 'booking_id', 'shipment_type')
    def _check_master_awb_matches_booking_awb(self):
        """Final hardening FF-76: Master yang punya booking_id (hasil
        action_create_job) HARUS memakai document yang EXACT sama dengan
        Booking-nya. Menangkap mismatch dari jalur mana pun (write
        document_id langsung -- sudah ditolak lebih awal di write() --
        ATAU perubahan booking_id/shipment_type lewat ORM/RPC lain). TIDAK
        live-sync/cascade -- kalau mismatch, tolak."""
        for rec in self:
            if rec.shipment_type == 'master' and rec.booking_id:
                if rec.document_id != rec.booking_id.document_id:
                    raise ValidationError(
                        "Master Job (%s) harus memakai AWB No. yang sama dengan "
                        "Booking-nya (%s)." % (rec.job_no, rec.booking_id.name)
                    )

    def _get_effective_booking(self):
        self.ensure_one()
        return self.booking_id or (
            self.master_job_id.booking_id if self.master_job_id else self.env['freight.air.booking']
        )

    @api.model
    def _prepare_house_vals_from_quotation(self, quotation, master=False):
        """FF-75: vals House AWB baru, diprefill dari Quotation aktif -- BUKAN
        dari Booking/Master. Mapping field mengikuti persis yang sudah ada di
        _action_convert_to_jobsheet_direct_air sebelum FF-75."""
        original = quotation.original_quotation_id or quotation
        all_variants = original | original.variant_ids
        vals = {
            'shipment_type': 'house',
            'sale_order_ids': [(6, 0, all_variants.ids)],
            'source_quotation_id': original.id,
            'freight_type': quotation.freight_type,
            'partner_id': quotation.partner_id.id if quotation.partner_id else False,
            'customer_ref': quotation.reference_number or quotation.client_order_ref or False,
            'term_payment': quotation.payment_term_id.id if quotation.payment_term_id else False,
            'company_id': quotation.company_id.id if quotation.company_id else self.env.company.id,
        }
        if master:
            vals['master_job_id'] = master.id
            # FF-79: House pertama dari Booking->Master mengikuti job_type_id
            # FINAL Master saat creation (copy sekali, bukan live-sync --
            # sama seperti Master sendiri mengambil dari Booking di
            # action_create_job(); Master/House boleh diubah manual setelah
            # ini tanpa saling mempengaruhi). Untuk direct Quotation->House
            # (master=False) job_type_id SENGAJA tidak diisi di sini --
            # dibiarkan resolve sendiri dari freight_type di atas lewat
            # auto-fill create() (freight.job.type.resolver.mixin).
            vals['job_type_id'] = master.job_type_id.id if master.job_type_id else False
        return vals

    def action_view_booking(self):
        self.ensure_one()
        booking = self._get_effective_booking()
        if not booking:
            return False
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith('_view_ref')}
        return {
            'name': _('Air Booking'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.air.booking',
            'res_id': booking.id,
            'view_mode': 'form',
            'context': ctx,
        }

    def action_view_sales_orders(self):
        self.ensure_one()
        orders = self.sale_order_ids
        if not orders:
            return False
        view_id = self.env.ref('freight_forwarding.view_air_quotation_form').id
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith('_view_ref')}
        ctx.update({
            'default_air_job_id': self.id,
            'default_is_freight_quotation': True,
            'default_freight_business_type': 'air',
        })
        return {
            'name': _('Sales Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form' if len(orders) == 1 else 'list,form',
            'views': [(view_id, 'form')] if len(orders) == 1 else [(False, 'list'), (view_id, 'form')],
            'domain': [('id', 'in', orders.ids)],
            'res_id': orders.id if len(orders) == 1 else False,
            'context': ctx,
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
                default_air_job_id=self.id,
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

    def action_same_as_consignee(self):
        self.ensure_one()
        if self.consignee_id:
            self.notify_party_id = self.consignee_id
    
    def action_same_as_customer(self):
        self.ensure_one()
        if self.partner_id:
            self.consignee_id = self.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        plan = None
        for vals in vals_list:
            if vals.get('job_no', _('New')) == _('New'):
                # Direction eksplisit menentukan sequence Import/Export.
                # Kalau freight_type kosong (Quotation Type belum diisi),
                # JANGAN diam-diam dianggap Export -- pakai sequence netral
                # supaya job_no tetap tergenerate tanpa salah klasifikasi.
                freight_type = vals.get('freight_type')
                if freight_type == 'export':
                    vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.job.job_no.exp') or _('New')
                elif freight_type == 'import':
                    vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.job.job_no.imp') or _('New')
                else:
                    vals['job_no'] = self.env['ir.sequence'].next_by_code('freight.air.job.job_no') or _('New')

            # FF-75: analytic HARUS sudah konsisten di vals SEBELUM
            # super().create() -- lihat komentar lengkap di
            # freight.sea.job.create() (hbl.py), pola identik di sini.
            if not vals.get('analytic_account_id'):
                master_job_id = vals.get('master_job_id')
                if master_job_id:
                    master = self.browse(master_job_id)
                    vals['analytic_account_id'] = master.analytic_account_id.id
                else:
                    if plan is None:
                        plan = self.env["account.analytic.plan"].search([], limit=1)
                        if not plan:
                            plan = self.env["account.analytic.plan"].create({"name": "Default"})
                    analytic_account = self.env['account.analytic.account'].create({
                        'name': vals.get('job_no'),
                        'plan_id': plan.id,
                        'company_id': vals.get('company_id') or self.env.company.id,
                        'partner_id': vals.get('partner_id') or False,
                    })
                    vals['analytic_account_id'] = analytic_account.id

        records = super(FreightAirHawb, self).create(vals_list)
        records._sync_analytic_to_related_docs()
        for rec in records:
            if rec.document_id:
                rec.document_id._mark_used(air_job=rec)
        return records

    def write(self, vals):
        if 'document_id' in vals:
            new_awb_id = vals.get('document_id')
            for rec in self:
                if (rec.shipment_type == 'master' and rec.booking_id
                        and rec.document_id and new_awb_id != rec.document_id.id):
                    raise ValidationError(
                        "Master Job (%s) dibuat dari Booking (%s) -- AWB No. tidak "
                        "boleh diedit independen dari Master." % (rec.job_no, rec.booking_id.name)
                    )
            # UAT revision (late assignment): Booking boleh Create Job tanpa
            # AWB (Master ikut kosong). Setelah itu, AWB HANYA boleh
            # di-assign lewat Master (Booking tetap bukan entry point --
            # lihat guard di freight.air.booking.write()) -- begitu
            # ter-assign, cascade ke Booking supaya satu chain berakhir pada
            # AWB Master yang sama. Cascade dilakukan SEBELUM super().write()
            # supaya _check_master_awb_matches_booking_awb melihat state
            # yang sudah konsisten begitu constrain jalan.
            for rec in self:
                if (rec.shipment_type == 'master' and rec.booking_id
                        and not rec.document_id and new_awb_id
                        and not rec.booking_id.document_id):
                    rec.booking_id.with_context(_awb_master_cascade=True).write(
                        {'document_id': new_awb_id}
                    )
        if 'master_job_id' in vals and 'analytic_account_id' not in vals:
            # FF-75: House mengikuti analytic Master -- disamakan di vals
            # SEBELUM super().write() supaya @api.constrains tidak melihat
            # state sementara yang mismatch.
            master_job_id = vals.get('master_job_id')
            if master_job_id:
                master = self.browse(master_job_id)
                vals['analytic_account_id'] = master.analytic_account_id.id
        res = super(FreightAirHawb, self).write(vals)
        if 'analytic_account_id' in vals:
            # FF-75: Master.analytic_account_id berubah -> cascade ke semua
            # House-nya (invariant juga dijaga keras oleh
            # _check_house_analytic_matches_master).
            for rec in self:
                if rec.shipment_type == 'master' and rec.house_job_ids:
                    stale_houses = rec.house_job_ids.filtered(
                        lambda h, rec=rec: h.analytic_account_id != rec.analytic_account_id
                    )
                    if stale_houses:
                        stale_houses.write({'analytic_account_id': rec.analytic_account_id.id})
        self._sync_analytic_to_related_docs()
        if 'document_id' in vals:
            for rec in self:
                if rec.document_id:
                    rec.document_id._mark_used(air_job=rec)
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
                    if hasattr(so, "air_job_id") and not so.air_job_id:
                        so.air_job_id = rec.id
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
                    if hasattr(po, "air_job_id") and not po.air_job_id:
                        po.air_job_id = rec.id
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
            moves |= self.env["account.move"].search([("air_job_id", "=", rec.id)])

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
                if hasattr(move, "air_job_id") and not move.air_job_id:
                    move.air_job_id = rec.id
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
