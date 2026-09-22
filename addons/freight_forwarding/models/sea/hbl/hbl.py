from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SeaHBL(models.Model):
    _name = "freight.sea.job"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "freight.sea.shipment.info.mixin",
        "freight.sea.vessel.details.mixin",
        "freight.sea.bl.info.mixin",
        "freight.commercial.group.mixin",
        "freight.job.type.resolver.mixin",
    ]
    _description = "Sea Job (Master/House)"
    _rec_name = "job_no"
    _job_type_business_type = "sea"
    _sql_constraints = [
        ("job_no_uniq", "unique(job_no)", "Job No. harus unik."),
        ("document_id_uniq", "unique(document_id)", "B/L ini sudah dipakai Job lain."),
    ]

    # FF-76 Step 2: canonical shared transport document relation (paralel
    # dengan Air freight.air.job.document_id). Master vs House sudah
    # dibedakan oleh `record_level` -- SATU field canonical ini dipakai
    # oleh keduanya, bukan master_bl_id/house_bl_id terpisah.
    document_id = fields.Many2one(
        "freight.transport.document",
        string="B/L No.",
        domain="[('transport_mode', '=', 'sea')]",
        tracking=True,
    )

    record_level = fields.Selection(
        [("master", "Master"), ("house", "House")],
        string="Shipment Type",
        default="house",
        required=True,
        tracking=True,
        help="Master: Job penuh (BL/Booking, shipment info, costing, dst. "
             "sendiri) yang berperan sebagai consolidation point, bisa "
             "menaungi banyak House. House: Job individual yang WAJIB "
             "berada di bawah satu Master lewat master_job_id -- House "
             "tidak boleh berdiri sendiri.",
    )
    master_job_id = fields.Many2one(
        "freight.sea.job",
        string="Master Job",
        domain="[('record_level', '=', 'master'), ('id', '!=', id)]",
        tracking=True,
        ondelete="restrict",
        help="Master Job tempat House ini bergabung. WAJIB terisi untuk "
             "House (House tidak boleh berdiri sendiri); kosong untuk "
             "Master itu sendiri.",
    )
    house_job_ids = fields.One2many(
        "freight.sea.job",
        "master_job_id",
        string="House Jobs",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )
    job_no = fields.Char(string="Job No.", required=True, default=lambda self: "New", copy=False, readonly=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Consignee / To",
        related="consignee_id",
        store=False,
        readonly=True,
    )
    partner_tel = fields.Char(string="Consignee Tel", compute="_compute_partner_contact_fields", readonly=True, store=False)
    partner_fax = fields.Char(string="Consignee Fax", compute="_compute_partner_contact_fields", readonly=True, store=False)
    notice_date = fields.Date(string="Notice Date")
    # FF-76 Step 2 (corrective pass): `bl_no` DIRETIRE sebagai canonical
    # source of truth -- lihat catatan setara di freight.sea.booking.bl_no.
    # Derived read-only alias dari document_id.document_no (Master maupun
    # House pakai relation canonical yang sama, dibedakan lewat
    # record_level), dipertahankan untuk compatibility display (report
    # QWeb, cargo_info.py, list/search) saja. TIDAK writable independen.
    bl_no = fields.Char(
        string="B/L No.",
        related="document_id.document_no",
        store=True,
        readonly=True,
    )
    carrier_id = fields.Many2one(
        "res.partner",
        string="Carrier / Shipping Line",
        related="shipping_line_id",
        store=False,
        readonly=True,
    )
    pol_id = fields.Many2one(
        "freight.port",
        string="POL",
        related="port_of_loading_id",
        store=False,
        readonly=True,
    )
    pod_id = fields.Many2one(
        "freight.port",
        string="POD",
        related="port_of_discharge_id",
        store=False,
        readonly=True,
    )
    do_ready_date = fields.Date(string="DO Ready On")
    port_code = fields.Char(string="Port Code")
    container_seal_ids = fields.Char(string="Container / Seal No.", compute="_compute_container_seal_ids", store=False)
    cargo_line_ids = fields.One2many(
        "freight.sea.job.cargo.info",
        "job_id",
        string="Cargo Lines",
        related="cargo_info_ids",
        readonly=True,
    )
    remarks = fields.Text(string="Remarks")

    sales_order_count = fields.Integer(string="Sales Order Count", compute="_compute_sales_order_count")
    purchase_order_count = fields.Integer(string="Purchase Order Count", compute="_compute_purchase_order_count")
    booking_count = fields.Integer(string="Booking Count", compute="_compute_booking_count")

    freight_type = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Type",
        required=True,
    )
    # FF-75 follow-up: `container_type` (FCL/LCL) dihapus -- duplicate
    # semantic dengan `ship_mode` (fields.Selection fcl/lcl) yang sudah ada
    # di freight.sea.shipment.info.mixin (di-inherit lewat _inherit di atas).
    # Override di sini murni untuk mempertahankan required=True yang dulu
    # ada di container_type -- ship_mode di mixin sendiri sengaja tidak
    # required (dipakai juga oleh Booking yang tidak mewajibkannya).
    ship_mode = fields.Selection(required=True)
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=False,
    )
    job_date = fields.Date(string="Job Date")
    job_city_id = fields.Many2one("res.city", string="Job City")
    from_city = fields.Many2one("res.city", string="From")
    origin_country_id = fields.Many2one("res.country", string="Origin Country")
    to_city = fields.Many2one("res.city", string="To")
    destination_country_id = fields.Many2one("res.country", string="Destination Country")
    no_of_original_bl = fields.Char(string="No. of Original B/L")
    obl_no = fields.Char(string="OB/L No.")
    original_bl_no = fields.Char(string="Original BL No.")
    bl_surrendered = fields.Boolean(string="BL Surrendered")
    delivery_type_id = fields.Many2one("account.incoterms", string="Delivery Type")
    # do_ready_on = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Do Ready On")
    do_ready_on = fields.Boolean(string="Do Ready On")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    customer_id = fields.Many2one("res.partner", string="Customer")
    customer_ref = fields.Char(string="Customer Reference")
    actual_shipper = fields.Boolean(string="Actual Shipper")
    term_payment = fields.Many2one("account.payment.term", string="Terms of Payment")
    export_sales_team_id = fields.Many2one(
        "res.partner",
        string="Export Sales Team",
        domain="[('category_id.name', '=', 'Sales Team')]"
    )
    analytic_account_id = fields.Many2one("account.analytic.account", string="Analytic Account")

    freight = fields.Selection(
        selection=[
            ("prepaid", "Prepaid"),
            ("collect", "Collect"),
        ],
        string="Freight",
    )
    
    remark = fields.Text(string="Remark")
    
    warehouse_location_id = fields.Many2one("stock.warehouse", string="Warehouse Location")
    total_packages_remark = fields.Char(string="Total No. of Packages/Units (in words)")
    pbm = fields.Char(string="PBM")

    sale_order_ids = fields.Many2many("sale.order", string="Sales Orders")
    purchase_order_ids = fields.Many2many("purchase.order", string="Purchase Orders")
    custom_permit_ids = fields.One2many("freight.sea.job.custom.permit", "job_id", string="Custom Permit")
    cargo_info_ids = fields.One2many("freight.sea.job.cargo.info", "job_id", string="Cargo Info")
    tax_refund_doc_ids = fields.One2many("freight.sea.job.tax.refund.doc", "job_id", string="Tax Refund Doc")
    invoice_ids = fields.One2many("freight.sea.job.invoice", "job_id", string="Invoice")
    debit_note_ids = fields.One2many("freight.sea.job.debit.note", "job_id", string="Debit Note")
    credit_note_ids = fields.One2many("freight.sea.job.credit.note", "job_id", string="Credit Note")
    provision_cost_ids = fields.One2many("freight.sea.job.provision.cost", "job_id", string="Provision Cost")
    vendor_invoice_ids = fields.One2many("freight.sea.job.vendor.invoice", "job_id", string="Vendor Invoice")
    vendor_debit_note_ids = fields.One2many("freight.sea.job.vendor.debit.note", "job_id", string="Vendor Debit Note")
    vendor_credit_note_ids = fields.One2many("freight.sea.job.vendor.credit.note", "job_id", string="Vendor Credit Note")
    cash_purchase_ids = fields.One2many("freight.sea.job.cash.purchase", "job_id", string="Cash Purchase")

    @api.depends("cargo_info_ids")
    def _compute_container_seal_ids(self):
        for rec in self:
            items = []
            for cargo in rec.cargo_info_ids:
                if cargo.container_no or cargo.seal_no:
                    items.append(f"{cargo.container_no or ''}/{cargo.seal_no or ''}".strip("/"))
            rec.container_seal_ids = ", ".join(items)

    @api.depends("consignee_id")
    def _compute_partner_contact_fields(self):
        for rec in self:
            rec.partner_tel = rec.consignee_id.phone or False if rec.consignee_id else False
            rec.partner_fax = rec.consignee_id.fax or False if rec.consignee_id else False

    @api.depends("sale_order_ids")
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    @api.depends("purchase_order_ids")
    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    @api.depends("booking_id", "master_job_id.booking_id")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = 1 if rec._get_effective_booking() else 0

    def _get_effective_booking(self):
        self.ensure_one()
        return self.booking_id or (
            self.master_job_id.booking_id if self.master_job_id else self.env["freight.sea.booking"]
        )

    # FF-75 semantic consistency: TIDAK override _get_source_quotation() --
    # Sea tidak punya Direct, jadi implementation base
    # freight.commercial.group.mixin (return self.source_quotation_id, tanpa
    # fallback lewat booking_id) sudah tepat apa adanya untuk Master maupun
    # House. Master bukan commercial owner Quotation manapun (source_quotation_id
    # sendiri memang selalu kosong untuk Master). House selalu punya
    # source_quotation_id sendiri (diisi langsung saat dibuat).

    @api.constrains("record_level", "master_job_id")
    def _check_master_house_hierarchy(self):
        for rec in self:
            if rec.record_level == "master" and rec.master_job_id:
                raise ValidationError("Master Job tidak boleh memiliki Master Job lain (master_job_id harus kosong).")
            if rec.record_level == "house" and not rec.master_job_id:
                raise ValidationError("House Job wajib menunjuk ke Master Job (master_job_id tidak boleh kosong).")
            if rec.master_job_id:
                if rec.master_job_id.id == rec.id:
                    raise ValidationError("Job tidak boleh menjadi Master Job untuk dirinya sendiri.")
                if rec.master_job_id.record_level != "master":
                    raise ValidationError("master_job_id harus menunjuk ke Job dengan Record Level 'Master'.")

    @api.constrains("record_level")
    def _check_master_cannot_become_house(self):
        """FF-75 follow-up: proteksi dari sisi parent -- Master yang sudah
        punya House tidak boleh diubah jadi House lewat write/RPC."""
        for rec in self:
            if rec.record_level == "house" and rec.house_job_ids:
                raise ValidationError(
                    "Job (%s) tidak bisa diubah dari Master menjadi House karena masih "
                    "memiliki House Job (%s)." % (rec.job_no, ", ".join(rec.house_job_ids.mapped("job_no")))
                )

    @api.constrains("master_job_id")
    def _check_fcl_single_house_on_attach(self):
        for rec in self:
            master = rec.master_job_id
            if master and master.ship_mode == "fcl":
                other_house_count = self.search_count([
                    ("master_job_id", "=", master.id),
                    ("id", "!=", rec.id),
                ])
                if other_house_count >= 1:
                    raise ValidationError(
                        "Sea FCL (%s) sudah memiliki 1 House Job. Tidak bisa menambahkan House lagi." % master.job_no
                    )

    @api.constrains("ship_mode", "house_job_ids")
    def _check_fcl_single_house_on_master(self):
        for rec in self:
            if rec.record_level == "master" and rec.ship_mode == "fcl" and len(rec.house_job_ids) > 1:
                raise ValidationError(
                    "Sea FCL (%s) hanya boleh memiliki maksimal 1 House Job." % rec.job_no
                )

    @api.model
    def _find_commercial_group_house(self, quotation):
        """Manual UAT follow-up FF-75: House Sea lain (record_level='house')
        yang source_quotation_id-nya berada di commercial group (root +
        seluruh currency variant) yang sama dengan `quotation`. Dipakai
        bersama oleh constraint model (_check_single_house_per_commercial_group)
        dan wizard Add to Master -- canonical check HARUS berdasarkan House +
        source quotation/commercial group, BUKAN sale_order.sea_job_id
        (singular, tidak menjamin 1:1) atau sea_job_ids compatibility mirror."""
        if not quotation:
            return self.browse()
        root = quotation.original_quotation_id or quotation
        group_ids = (root | root.variant_ids).ids
        return self.search([
            ("record_level", "=", "house"),
            ("source_quotation_id", "in", group_ids),
        ])

    @api.constrains("record_level", "source_quotation_id")
    def _check_single_house_per_commercial_group(self):
        """Manual UAT follow-up FF-75: 1 commercial quotation group (root +
        seluruh currency variant) maksimal punya 1 House Sea. Berlaku murni
        untuk House -- Master tidak ikut rule ini (source_quotation_id Master
        selalu kosong, lihat commercial_group_mixin). Ditangkap lewat
        create() MAUPUN write() (constrains, bukan hanya wizard)."""
        for rec in self:
            if rec.record_level != "house" or not rec.source_quotation_id:
                continue
            duplicates = rec._find_commercial_group_house(rec.source_quotation_id) - rec
            if duplicates:
                root = rec.source_quotation_id.original_quotation_id or rec.source_quotation_id
                raise ValidationError(
                    "Quotation %s (beserta seluruh currency variant-nya) sudah "
                    "memiliki House Job (%s) -- satu Quotation hanya boleh "
                    "menghasilkan maksimal 1 House Job." % (root.name, duplicates[0].job_no)
                )

    @api.constrains("document_id")
    def _check_document_chain(self):
        """FF-76 Step 2: sama persis dengan pola Air (freight.air.job) --
        AWB/BL availability/ownership rule terpusat di sini.
        - SQL unique constraint (document_id_uniq) sudah menolak 2 Job
          mana pun (Master/House) berbagi document yang sama.
        - Satu-satunya exception LEGAL: Master hasil action_create_job dari
          Booking yang SAMA memakai document yang sudah dipakai Booking
          tersebut (chain Booking->Master).
        - Kalau document sudah pernah dipakai (is_used) oleh chain lain,
          tolak -- one-time semantic, bukan cuma cek relation kosong."""
        for rec in self:
            doc = rec.document_id
            if not doc:
                continue
            if doc.transport_mode != "sea":
                raise ValidationError(
                    "B/L %s bertipe '%s' -- Sea Job hanya boleh memakai "
                    "document Sea." % (doc.document_no, doc.transport_mode)
                )
            if not doc.is_used:
                continue
            legal = doc.used_sea_job_id == rec or (
                rec.record_level == "master"
                and doc.used_sea_booking_id
                and rec.booking_id == doc.used_sea_booking_id
            )
            if not legal:
                raise ValidationError(
                    "B/L %s sudah pernah digunakan dan tidak dapat dipakai "
                    "ulang oleh Job ini." % doc.document_no
                )

    @api.constrains("document_id", "booking_id", "record_level")
    def _check_master_document_matches_booking_document(self):
        """FF-76 Step 2: sama persis dengan pola Air -- Master yang punya
        booking_id (hasil action_create_job) HARUS memakai document yang
        EXACT sama dengan Booking-nya. TIDAK live-sync/cascade -- kalau
        mismatch, tolak."""
        for rec in self:
            if rec.record_level == "master" and rec.booking_id:
                if rec.document_id != rec.booking_id.document_id:
                    raise ValidationError(
                        "Master Job (%s) harus memakai B/L No. yang sama dengan "
                        "Booking-nya (%s)." % (rec.job_no, rec.booking_id.name)
                    )

    @api.constrains("analytic_account_id", "master_job_id")
    def _check_house_analytic_matches_master(self):
        """FF-75: invariant keras -- House TIDAK BOLEH punya analytic account
        yang beda dari Master-nya, lewat jalur apa pun (create/write/RPC).
        create()/write() di bawah selalu menyamakannya otomatis; constraint
        ini murni jaring pengaman supaya invariant ini tidak bisa dilanggar
        diam-diam oleh kode lain di masa depan."""
        for rec in self:
            if rec.master_job_id and rec.analytic_account_id != rec.master_job_id.analytic_account_id:
                raise ValidationError(
                    "House (%s) tidak boleh memiliki Analytic Account independen -- "
                    "harus sama dengan Master Job (%s)." % (rec.job_no, rec.master_job_id.job_no)
                )

    @api.model
    def _prepare_house_vals_from_quotation(self, quotation, master=False):
        """FF-75: vals House Job baru, diprefill dari Quotation aktif -- BUKAN
        dari Booking/Master. Dipakai bersama oleh flow Export (House pertama
        dari Booking.source_quotation_id), Import (House pertama dari
        Quotation langsung), dan wizard Add to Master (House tambahan).

        Mapping field mengikuti persis yang sudah ada di
        _action_convert_to_jobsheet_direct_sea sebelum FF-75 -- tidak
        menambah mapping baru yang belum punya source existing."""
        original = quotation.original_quotation_id or quotation
        all_variants = original | original.variant_ids
        vals = {
            "record_level": "house",
            "sale_order_ids": [(6, 0, all_variants.ids)],
            "source_quotation_id": original.id,
            "freight_type": quotation.freight_type,
            "ship_mode": quotation.sea_ship_mode,
            "customer_id": quotation.partner_id.id if quotation.partner_id else False,
            "term_payment": quotation.payment_term_id.id if quotation.payment_term_id else False,
            "job_date": fields.Date.context_today(self),
            "company_id": quotation.company_id.id if quotation.company_id else self.env.company.id,
        }
        if master:
            vals["master_job_id"] = master.id
            # FF-79: House pertama dari Booking->Master mengikuti job_type_id
            # FINAL Master saat creation (copy sekali, bukan live-sync --
            # sama seperti Master sendiri mengambil dari Booking di
            # action_create_job(); Master/House boleh diubah manual setelah
            # ini tanpa saling mempengaruhi). Untuk direct Quotation->House
            # (master=False) job_type_id SENGAJA tidak diisi di sini --
            # dibiarkan resolve sendiri dari freight_type/ship_mode di atas
            # lewat auto-fill create() (freight.job.type.resolver.mixin).
            vals["job_type_id"] = master.job_type_id.id if master.job_type_id else False
        return vals

    @api.onchange("from_city")
    def _onchange_from_city(self):
        for rec in self:
            if rec.from_city.country_id:
                rec.origin_country_id = rec.from_city.country_id

    @api.onchange("to_city")
    def _onchange_to_city(self):
        for rec in self:
            if rec.to_city.country_id:
                rec.destination_country_id = rec.to_city.country_id

    def action_active(self):
        for rec in self:
            rec.state = "active"

    def action_close(self):
        for rec in self:
            rec.state = "closed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    def action_view_sales_orders(self):
        self.ensure_one()
        orders = self.sale_order_ids
        if not orders:
            return False

        view_id = self.env.ref("freight_forwarding.view_sea_quotation_form").id
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({
            "default_sea_job_id": self.id,
            "default_is_freight_quotation": True,
            "default_freight_business_type": "sea",
        })
        return {
            "name": "Sales Orders",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form" if len(orders) == 1 else "list,form",
            "views": [(view_id, "form")] if len(orders) == 1 else [(False, "list"), (view_id, "form")],
            "domain": [("id", "in", orders.ids)],
            "res_id": orders.id if len(orders) == 1 else False,
            "context": ctx,
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        orders = self.purchase_order_ids
        if not orders:
            return False

        return {
            "name": "Purchase Orders",
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_mode": "form" if len(orders) == 1 else "list,form",
            "domain": [("id", "in", orders.ids)],
            "res_id": orders.id if len(orders) == 1 else False,
            "context": dict(
                self.env.context,
                default_sea_job_id=self.id,
            ),
        }

    def action_view_booking(self):
        self.ensure_one()
        booking = self._get_effective_booking()
        if not booking:
            return False

        return {
            "name": "Sea Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "context": dict(self.env.context),
        }

    @api.model_create_multi
    def create(self, vals_list):
        plan = None
        for vals in vals_list:
            sequence_date = fields.Date.to_date(
                vals.get("job_date") or fields.Date.context_today(self)
            )
            if not vals.get("job_no") or vals.get("job_no") == "New":
                freight_type = vals.get("freight_type")
                if not freight_type and vals.get("booking_id"):
                    booking = self.env["freight.sea.booking"].browse(vals.get("booking_id"))
                    freight_type = booking.freight_type

                seq_code = "freight.sea.job.job_no.exp" if freight_type == "export" else "freight.sea.job.job_no.imp"
                vals["job_no"] = self.env["ir.sequence"].next_by_code(
                    seq_code, sequence_date=sequence_date
                ) or "New"

            # FF-75: analytic HARUS sudah konsisten di vals SEBELUM super().create()
            # -- Odoo memvalidasi @api.constrains (termasuk
            # _check_house_analytic_matches_master) sesaat setelah INSERT, di
            # dalam super().create() itu sendiri, jauh sebelum baris manapun
            # SETELAH super().create() sempat jalan. Menyamakan analytic_account_id
            # di sini (bukan lewat rec.analytic_account_id = ... pasca-create)
            # supaya constraint tidak pernah melihat state sementara yang mismatch.
            if not vals.get("analytic_account_id"):
                master_job_id = vals.get("master_job_id")
                if master_job_id:
                    # House tidak pernah membuat analytic account independen --
                    # analytic efektifnya selalu ikut Master.
                    master = self.browse(master_job_id)
                    vals["analytic_account_id"] = master.analytic_account_id.id
                else:
                    if plan is None:
                        plan = self.env["account.analytic.plan"].search([], limit=1)
                        if not plan:
                            plan = self.env["account.analytic.plan"].create({"name": "Default"})
                    analytic_acc = self.env["account.analytic.account"].create({
                        "name": vals.get("job_no"),
                        "plan_id": plan.id,
                        "partner_id": vals.get("customer_id") or False,
                        "company_id": vals.get("company_id") or self.env.company.id,
                    })
                    vals["analytic_account_id"] = analytic_acc.id

        records = super().create(vals_list)
        records._sync_analytic_to_related_docs()
        for rec in records:
            if rec.document_id:
                rec.document_id._mark_used(sea_job=rec)
        return records

    def write(self, vals):
        if "document_id" in vals:
            new_doc_id = vals.get("document_id")
            for rec in self:
                if (rec.record_level == "master" and rec.booking_id
                        and rec.document_id and new_doc_id != rec.document_id.id):
                    raise ValidationError(
                        "Master Job (%s) dibuat dari Booking (%s) -- B/L No. tidak "
                        "boleh diedit independen dari Master." % (rec.job_no, rec.booking_id.name)
                    )
            # FF-76 Step 2 (late assignment): sama persis dengan pola Air --
            # kalau Booking dan Master sama-sama masih kosong, assign B/L
            # lewat Master harus ikut mencerminkan ke Booking-nya. Cascade
            # dilakukan SEBELUM super().write() supaya
            # _check_master_document_matches_booking_document melihat state
            # yang sudah konsisten begitu constrain jalan.
            for rec in self:
                if (rec.record_level == "master" and rec.booking_id
                        and not rec.document_id and new_doc_id
                        and not rec.booking_id.document_id):
                    rec.booking_id.with_context(_sea_document_cascade=True).write(
                        {"document_id": new_doc_id}
                    )
        if "master_job_id" in vals and "analytic_account_id" not in vals:
            # FF-75: House mengikuti analytic Master -- disamakan di vals
            # SEBELUM super().write() supaya @api.constrains tidak melihat
            # state sementara yang mismatch (lihat komentar setara di create()).
            master_job_id = vals.get("master_job_id")
            if master_job_id:
                master = self.browse(master_job_id)
                vals["analytic_account_id"] = master.analytic_account_id.id
        res = super().write(vals)
        if "document_id" in vals:
            for rec in self:
                if rec.document_id:
                    rec.document_id._mark_used(sea_job=rec)
        if "analytic_account_id" in vals:
            # FF-75: Master.analytic_account_id berubah -> cascade ke semua
            # House-nya, supaya tidak ada House yang nyangkut di nilai lama
            # (invariant ini juga dijaga keras oleh _check_house_analytic_matches_master).
            for rec in self:
                if rec.record_level == "master" and rec.house_job_ids:
                    stale_houses = rec.house_job_ids.filtered(
                        lambda h, rec=rec: h.analytic_account_id != rec.analytic_account_id
                    )
                    if stale_houses:
                        stale_houses.write({"analytic_account_id": rec.analytic_account_id.id})
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
                    if hasattr(so, "sea_job_id") and not so.sea_job_id:
                        so.sea_job_id = rec.id
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
                    if hasattr(po, "sea_job_id") and not po.sea_job_id:
                        po.sea_job_id = rec.id
                    for line in po.order_line:
                        if not line.analytic_distribution:
                            self.env.cr.execute(
                                "UPDATE purchase_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(["analytic_distribution"])

            # 3. Sync to Invoices / Vendor Bills (account.move & lines)
            moves = self.env["account.move"]
            if rec.purchase_order_ids:
                moves |= rec.purchase_order_ids.mapped("invoice_ids")
            if rec.sale_order_ids:
                moves |= rec.sale_order_ids.mapped("invoice_ids")
            moves |= self.env["account.move"].search([("sea_job_id", "=", rec.id)])
            
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
                if hasattr(move, "sea_job_id") and not move.sea_job_id:
                    move.sea_job_id = rec.id
                for line in move.invoice_line_ids:
                    if not line.analytic_distribution and line.display_type not in ("line_section", "line_note"):
                        self.env.cr.execute(
                            "UPDATE account_move_line SET analytic_distribution = %s WHERE id = %s",
                            (json.dumps(distribution), line.id)
                        )
                        line.invalidate_recordset(["analytic_distribution"])
