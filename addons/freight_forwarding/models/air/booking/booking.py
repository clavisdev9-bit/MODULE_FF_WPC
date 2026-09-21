from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FreightAirBooking(models.Model):
    _name = 'freight.air.booking'
    _description = 'Air Freight Booking'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'freight.air.awb.info.mixin',
        'freight.air.shipment.info.mixin',
        'freight.air.cargo.info.mixin',
        'freight.commercial.group.mixin',
    ]
    _order = 'id desc'
    _sql_constraints = [
        ('document_id_uniq', 'unique(document_id)',
         'AWB ini sudah dipakai Booking lain.'),
    ]

    name = fields.Char(string='Booking No.', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    booking_date = fields.Datetime(string='Booking Date', default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    
    # FF-73 hardening: TIDAK ada default -- business field yang tidak
    # diberikan tidak boleh diam-diam diklasifikasikan ke arah tertentu.
    # Direction Export/Import untuk create dari menu tetap datang lewat
    # context default_freight_type (lihat views/air/booking/booking.xml),
    # bukan dari default field ini.
    freight_type = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export')
    ], string='Type', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    customer_reference = fields.Char(string='Customer Reference', tracking=True)
    
    telephone = fields.Char(string='Telephone', related='partner_id.phone', readonly=False, store=True)
    email = fields.Char(string='Email')
    is_nomination = fields.Boolean(string='Nomination Cargo')
    nomination_remark = fields.Char(string='Nomination Remark')
    booking_from = fields.Char(string='Booking From')

    payment_term_id = fields.Many2one('account.payment.term', string='Credit Term')
    salesman_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    sale_order_ids = fields.Many2many(
        'sale.order',
        string='Sales Orders',
    )
    sales_order_count = fields.Integer(
        string='Sales Order Count',
        compute='_compute_sales_order_count',
    )

    booking_remark = fields.Text(string='Booking Remark')
    footnote = fields.Text(string='Footnote')

    # Job / AWB References
    job_no = fields.Char(
        string='Job No.',
        compute='_compute_job_no',
        help='Job No. Master Job yang terkait Booking ini (FF-76). Kosong '
             'sebelum Master dibuat lewat Create Job; bukan identity '
             'independen Booking sendiri.',
    )
    document_id = fields.Many2one(
        'freight.transport.document',
        string='AWB No.',
        domain="[('transport_mode', '=', 'air')]",
        tracking=True,
    )

    # Relational Tables
    flight_routing_ids = fields.One2many('freight.air.booking.flight.routing', 'booking_id', string='Flight Routings')
    dimension_ids = fields.One2many('freight.air.booking.dimension', 'booking_id', string='Dimensions')
    air_job_ids = fields.One2many('freight.air.job', 'booking_id', string='Air Jobsheets (HAWBs)')
    air_job_count = fields.Integer(string='Jobsheet Count', compute='_compute_hawb_count')

    @api.depends('sale_order_ids')
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    @api.depends('air_job_ids.job_no', 'air_job_ids.shipment_type')
    def _compute_job_no(self):
        """FF-76: Booking tidak lagi punya identity job_no independen --
        menampilkan Job No. Master Job terkait (kosong sebelum Master ada)."""
        for rec in self:
            master = rec.air_job_ids.filtered(lambda j: j.shipment_type == 'master')[:1]
            rec.job_no = master.job_no if master else False

    @api.constrains('document_id')
    def _check_awb_master_chain(self):
        """FF-76: AWB availability/ownership -- satu transport document
        hanya boleh dipakai oleh SATU Booking. Kalau document ini sudah
        pernah dipakai (is_used) oleh Booking LAIN (termasuk yang
        relation-nya sudah dilepas), tolak -- one-time semantic, bukan cuma
        cek relation kosong. SQL unique constraint (document_id_uniq) sudah
        menangani duplikasi antar Booking yang relation-nya masih aktif;
        constrain ini menutup celah reuse setelah document dilepas.

        UAT revision (late assignment): chain bisa juga terbentuk dari arah
        Master duluan (Booking kosong saat Create Job, AWB baru di-assign
        belakangan lewat Master -- lihat freight.air.job.write()). Dalam
        kasus itu `used_air_job_id` yang jadi pointer pertama, bukan
        `used_air_booking_id` -- keduanya legal selama Job tsb memang
        Master milik Booking ini."""
        for rec in self:
            awb = rec.document_id
            if not awb:
                continue
            if awb.transport_mode != 'air':
                raise ValidationError(
                    "AWB %s bertipe '%s' -- Air Booking hanya boleh memakai "
                    "AWB Type Air." % (awb.document_no, awb.transport_mode)
                )
            if not awb.is_used:
                continue
            legal = awb.used_air_booking_id == rec or (
                awb.used_air_job_id and awb.used_air_job_id.booking_id == rec
            )
            if not legal:
                raise ValidationError(
                    "AWB %s sudah pernah digunakan dan tidak dapat dipakai "
                    "ulang oleh Booking ini." % awb.document_no
                )

    def action_view_sales_orders(self):
        self.ensure_one()
        orders = self.sale_order_ids
        if not orders:
            return False

        view_id = self.env.ref("freight_forwarding.view_air_quotation_form").id
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({
            "default_is_freight_quotation": True,
            "default_freight_business_type": "air",
        })
        return {
            "name": _("Sales Orders"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form" if len(orders) == 1 else "list,form",
            "views": [(view_id, "form")] if len(orders) == 1 else [(False, "list"), (view_id, "form")],
            "domain": [("id", "in", orders.ids)],
            "res_id": orders.id if len(orders) == 1 else False,
            "context": ctx,
        }

    def _compute_hawb_count(self):
        for rec in self:
            rec.air_job_count = len(rec.air_job_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('freight.air.booking') or _('New')
        records = super(FreightAirBooking, self).create(vals_list)
        for rec in records:
            if rec.document_id:
                rec.document_id._mark_used(air_booking=rec)
        return records

    def write(self, vals):
        if 'document_id' in vals and not self.env.context.get('_awb_master_cascade'):
            # UAT revision: cascade write dari freight.air.job.write() (late
            # assignment Master -> Booking) sengaja melewati guard ini lewat
            # context flag -- itulah satu-satunya jalur yang boleh mengubah
            # AWB Booking setelah Master terbentuk (Booking sendiri TETAP
            # bukan entry point perubahan AWB, lihat komentar di
            # freight.air.job.write()).
            new_awb_id = vals.get('document_id')
            for rec in self:
                if new_awb_id == rec.document_id.id:
                    continue
                master = rec.air_job_ids.filtered(lambda j: j.shipment_type == 'master')
                if master:
                    raise ValidationError(
                        "Booking %s sudah memiliki Master Job (%s) -- AWB No. tidak "
                        "boleh diubah lagi setelah Master terbentuk. Assign AWB lewat "
                        "Master Job." % (rec.name, master[:1].job_no)
                    )
        res = super(FreightAirBooking, self).write(vals)
        if 'document_id' in vals:
            for rec in self:
                if rec.document_id:
                    rec.document_id._mark_used(air_booking=rec)
        return res

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

    def action_create_job(self):
        """Manual UAT follow-up FF-75 (Section 2): Air Booking -> Create Job
        SELALU berarti Booking -> Master -> House, tidak pernah Direct.
        Direct AWB TIDAK dibuat lewat Booking -- Direct AWB dibuat langsung
        sebagai freight.air.job berdiri sendiri lewat flow/menu Direct AWB
        (lihat _action_convert_to_jobsheet_direct_air di AirQuotation),
        tanpa lewat Booking sama sekali. Karena itu branching
        `is_direct = self.shipment_type == 'direct'` yang sebelumnya ada di
        sini DIHAPUS -- method ini sekarang murni membuat/mengambil Master
        Job (idempotent) dan House Job PERTAMA otomatis dari
        Booking.source_quotation_id."""
        self.ensure_one()

        master = self.env['freight.air.job'].search(
            [('booking_id', '=', self.id), ('shipment_type', '=', 'master')],
            limit=1,
            order='id desc',
        )
        if master:
            if not master.house_job_ids and self.source_quotation_id:
                house_vals = self.env['freight.air.job']._prepare_house_vals_from_quotation(
                    self.source_quotation_id, master=master
                )
                self.env['freight.air.job'].create(house_vals)
            return {
                'name': _('Air Job'),
                'type': 'ir.actions.act_window',
                'res_model': 'freight.air.job',
                'res_id': master.id,
                'view_mode': 'form',
                'target': 'current',
            }

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
            # FF-75 follow-up (Section E): Master TIDAK boleh mengambil
            # Customer dari Booking secara otomatis -- semantic Customer
            # Master consolidation belum dipastikan.
            'partner_id': False,
            'customer_ref': self.customer_reference,
            'is_nomination': self.is_nomination,
            'nomination_remark': self.nomination_remark,
            'term_payment': self.payment_term_id.id if self.payment_term_id else False,
            'salesman_id': self.salesman_id.id if self.salesman_id else False,
            # FF-76: Master harus memakai AWB Master yang EXACT sama dengan
            # Booking (legal chain exception), atau kosong kalau Booking
            # belum punya AWB (late assignment lewat Master, lihat
            # freight.air.job.write()).
            'document_id': self.document_id.id if self.document_id else False,
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
            'shipment_type': 'master',
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
        # FF-75 follow-up (Section D): Master TIDAK boleh menerima
        # sale_order_ids Booking untuk commercial ownership -- House
        # (bukan Master) yang menjadi Job commercial untuk Q1 (dari
        # source_quotation_id-nya sendiri, lihat _prepare_house_vals_from_quotation).
        job = self.env['freight.air.job'].create(hawb_vals)

        if not job.house_job_ids and self.source_quotation_id:
            house_vals = self.env['freight.air.job']._prepare_house_vals_from_quotation(
                self.source_quotation_id, master=job
            )
            self.env['freight.air.job'].create(house_vals)

        return {
            'name': _('Air Job'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.air.job',
            'res_id': job.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_jobs(self):
        self.ensure_one()
        hawbs = self.air_job_ids
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({"default_booking_id": self.id})
        return {
            'name': _('Air Jobsheets (HAWBs)'),
            'type': 'ir.actions.act_window',
            'res_model': 'freight.air.job',
            'view_mode': 'form' if len(hawbs) == 1 else 'list,form',
            'domain': [('id', 'in', hawbs.ids)],
            'res_id': hawbs.id if len(hawbs) == 1 else False,
            'context': ctx,
        }

    action_create_jobsheet = action_create_job
    action_view_jobsheets = action_view_jobs


