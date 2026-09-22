from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SeaBooking(models.Model):
    _name = "freight.sea.booking"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "freight.sea.shipment.info.mixin",
        "freight.sea.vessel.details.mixin",
        "freight.sea.bl.info.mixin",
        "freight.commercial.group.mixin",
        "freight.job.type.resolver.mixin",
    ]
    _description = "Sea Booking"
    _rec_name = "name"
    _job_type_business_type = "sea"
    _sql_constraints = [
        ("document_id_uniq", "unique(document_id)",
         "B/L ini sudah dipakai Booking lain."),
    ]

    # FF-76 Step 2: canonical shared transport document relation (paralel
    # dengan Air). SATU-SATUNYA writable source of truth untuk B/L --
    # `bl_no` di bawah adalah derived read-only alias, lihat definisinya.
    document_id = fields.Many2one(
        "freight.transport.document",
        string="B/L No.",
        domain="[('transport_mode', '=', 'sea')]",
        tracking=True,
    )



    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )

    # Field relasi narik data Jobsheet (HBL) yang terkait sama Booking ini
    sea_job_ids = fields.One2many("freight.sea.job", "booking_id", string="Sea Jobsheets")

    # Field count buat trigger sembunyi/tampil tombol
    sea_job_count = fields.Integer(string="Jobsheet Count", compute="_compute_hbl_count")

    # Field buat show quotation (one-to-many relationship)
    sales_order_count = fields.Integer(
        string="Sales Order Count", compute="_compute_sales_order_count"
    )

    @api.depends("sea_job_ids")
    def _compute_hbl_count(self):
        for rec in self:
            rec.sea_job_count = len(rec.sea_job_ids)

    @api.depends("sale_order_ids")
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    @api.depends("sea_job_ids.job_no", "sea_job_ids.record_level")
    def _compute_job_no(self):
        """FF-76: Booking tidak lagi punya identity job_no independen --
        menampilkan Job No. Master Job terkait (kosong sebelum Master ada)."""
        for rec in self:
            master = rec.sea_job_ids.filtered(lambda j: j.record_level == "master")[:1]
            rec.job_no = master.job_no if master else False

    @api.constrains("document_id")
    def _check_document_chain(self):
        """FF-76 Step 2: sama persis dengan pola Air (freight.air.booking)
        -- satu transport document hanya boleh dipakai oleh SATU Sea
        Booking. Kalau document ini sudah pernah dipakai (is_used) oleh
        Booking LAIN (termasuk yang relation-nya sudah dilepas), tolak --
        one-time semantic. SQL unique constraint (document_id_uniq) sudah
        menangani duplikasi antar Booking yang relation-nya masih aktif;
        constrain ini menutup celah reuse setelah document dilepas.

        Late assignment (chain terbentuk dari arah Master duluan) juga
        legal selama Job tsb memang Master milik Booking ini -- lihat
        `used_sea_job_id`."""
        for rec in self:
            doc = rec.document_id
            if not doc:
                continue
            if doc.transport_mode != "sea":
                raise ValidationError(
                    "B/L %s bertipe '%s' -- Sea Booking hanya boleh memakai "
                    "document Sea." % (doc.document_no, doc.transport_mode)
                )
            if not doc.is_used:
                continue
            legal = doc.used_sea_booking_id == rec or (
                doc.used_sea_job_id and doc.used_sea_job_id.booking_id == rec
            )
            if not legal:
                raise ValidationError(
                    "B/L %s sudah pernah digunakan dan tidak dapat dipakai "
                    "ulang oleh Booking ini." % doc.document_no
                )



    @api.onchange("from_city")
    def _onchange_from_city(self):
        for rec in self:
            if rec.from_city.country_id:
                rec.origin_country_id = rec.from_city.country_id

    @api.onchange("to_city")
    def _onchange_to_city(self):
        for rec in self:
            rec.destination_country_id = rec.to_city.country_id

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    # Fungsi pas tombol Jobsheet di klik
    def action_view_jobs(self):
        self.ensure_one()
        hbls = self.sea_job_ids

        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.job",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context, default_booking_id=self.id, default_company_id=self.company_id.id),
        }

    def action_view_sales_orders(self):
        self.ensure_one()
        orders = self.sale_order_ids
        if not orders:
            return False

        return {
            "name": "Sales Orders",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form" if len(orders) == 1 else "list,form",
            "domain": [("id", "in", orders.ids)],
            "res_id": orders.id if len(orders) == 1 else False,
            "context": dict(self.env.context),
        }

    # Header Information
    freight_type = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Type",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    name = fields.Char(
        string="Booking No.",
        required=True,
        default=lambda self: "New",
        copy=False,
    )
    booking_date = fields.Datetime(string="Date & Time")
    # FF-76 Step 2 (corrective pass): `bl_no` DIRETIRE sebagai canonical
    # source of truth -- sekarang derived read-only alias dari
    # `document_id.document_no`, dipertahankan HANYA untuk compatibility
    # display (report QWeb, list/search) yang butuh membaca "own B/L"
    # tanpa join manual. TIDAK writable independen lagi -- `related` tanpa
    # `readonly=False` tidak membuat inverse, jadi satu-satunya cara
    # mengubah nilai ini adalah lewat `document_id`.
    bl_no = fields.Char(
        string="B/L No.",
        related="document_id.document_no",
        store=True,
        readonly=True,
    )
    job_no = fields.Char(
        string="Job No.",
        compute="_compute_job_no",
        help="Job No. Master Job yang terkait Booking ini (FF-76). Kosong "
             "sebelum Master dibuat lewat Create Job; bukan identity "
             "independen Booking sendiri.",
    )
    nomination_cargo = fields.Boolean(string="Nomination Cargo")
    # FF-75 follow-up: `container_type` (FCL/LCL) dihapus -- duplicate
    # semantic dengan `ship_mode` yang sudah ada lewat
    # freight.sea.shipment.info.mixin (_inherit di atas).
    job_date = fields.Date(string="Job Date")
    import_job_no = fields.Char(string="Import Job Number (Optional)")
    railing = fields.Boolean(string="Railing")

    # Customer & Contact Data
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer Name",
    )
    customer_reference = fields.Char(string="Customer Reference")
    phone = fields.Char(related="partner_id.phone", string="Phone Number")
    email = fields.Char(related="partner_id.email", string="Email Address")
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
    )
    sale_order_ids = fields.Many2many(
        "sale.order",
        string="Sales Orders",
    )

    # Location & Route
    # NOTE: port_of_loading_id, port_of_discharge_id, commodity_id, etd, eta,
    # eta_jkt ada di freight.sea.shipment.info.mixin (ditampilkan di tab
    # Shipment Info). Definisi di sini hanya untuk field yang khas Booking.
    destination_country_id = fields.Many2one(
        "res.country", string="Destination Country"
    )
    origin_country_id = fields.Many2one(
        "res.country", string="Origin Country"
    )
    from_city = fields.Many2one("res.city", string="From")
    to_city = fields.Many2one("res.city", string="To")
    delivery_type_id = fields.Many2one(
        "account.incoterms", string="Delivery Type"
    )

    # Vessel Information
    pod_port_id = fields.Many2one("freight.port", string="Port of Delivery")

    # Notebook
    # NOTE (FF-22): field shipment_info_ids (One2many ke
    # freight.sea.booking.shipment.info) DIHAPUS. Model perantaranya sudah
    # dihapus; field-fieldnya sekarang ada langsung di sini lewat
    # freight.sea.shipment.info.mixin (lihat _inherit di atas).
    cargo_info_ids = fields.One2many(
        "freight.sea.booking.cargo.info",
        "booking_id",
        string="Cargo Info",
    )

    purchase_order_ids = fields.Many2many(
        "purchase.order",
        string="Purchase Orders",
    )
    extra_info_ids = fields.One2many(
        "freight.sea.booking.extra.info",
        "booking_id",
        string="Extra Info",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "freight.sea.booking"
                ) or "New"
        records = super().create(vals_list)
        for rec in records:
            if rec.document_id:
                rec.document_id._mark_used(sea_booking=rec)
        return records

    def write(self, vals):
        if "document_id" in vals and not self.env.context.get("_sea_document_cascade"):
            # FF-76 Step 2: pola sama dengan Air -- cascade write dari
            # freight.sea.job.write() (late assignment Master -> Booking)
            # sengaja melewati guard ini lewat context flag. Itulah
            # satu-satunya jalur yang boleh mengubah document Booking
            # setelah Master terbentuk (Booking sendiri TETAP bukan entry
            # point perubahan document, lihat komentar di
            # freight.sea.job.write()).
            new_doc_id = vals.get("document_id")
            for rec in self:
                if new_doc_id == rec.document_id.id:
                    continue
                master = rec.sea_job_ids.filtered(lambda j: j.record_level == "master")
                if master:
                    raise ValidationError(
                        "Booking %s sudah memiliki Master Job (%s) -- B/L No. tidak "
                        "boleh diubah lagi setelah Master terbentuk. Assign B/L lewat "
                        "Master Job." % (rec.name, master[:1].job_no)
                    )
        res = super().write(vals)
        if "document_id" in vals:
            for rec in self:
                if rec.document_id:
                    rec.document_id._mark_used(sea_booking=rec)
        return res

    def _copy_records_to_hbl(self, source_records, target_model_name, target_field_name, extra_values=None, excluded_fields=None):
        target_model = self.env[target_model_name]
        excluded_fields = set(excluded_fields or [])
        extra_values = extra_values or {}

        for source_record in source_records:
            values = source_record.copy_data(default=extra_values)[0]
            for field_name in list(values.keys()):
                if field_name in excluded_fields or field_name not in target_model._fields:
                    values.pop(field_name, None)
            values[target_field_name] = extra_values[target_field_name]
            target_model.create(values)

    def _copy_cargo_info_lines_to_hbl(self, booking_cargo_info_records, hbl):
        hbl_cargo_model = self.env["freight.sea.job.cargo.info"]

        for booking_cargo_info in booking_cargo_info_records:
            cargo_values = booking_cargo_info.copy_data(default={"job_id": hbl.id})[0]
            for field_name in ["booking_id", "sale_order_ids"]:
                cargo_values.pop(field_name, None)
            for field_name in list(cargo_values.keys()):
                if field_name not in hbl_cargo_model._fields:
                    cargo_values.pop(field_name, None)
            cargo_values["job_id"] = hbl.id
            hbl_cargo_model.create(cargo_values)

    def _copy_booking_data_to_hbl(self, booking, hbl):
        # NOTE (FF-22): pemanggilan copy shipment_info_ids DIHAPUS di sini
        # karena model freight.sea.booking.shipment.info /
        # freight.sea.job.shipment.info sudah tidak ada. Field-field
        # shipment info sekarang langsung ada di Booking & HBL (lewat mixin),
        # jadi tidak perlu proses copy antar model perantara lagi.


        header_fields = [
            # FF-76 Step 2: "bl_no" DIHAPUS dari list ini -- sekarang derived
            # read-only alias dari document_id (lihat definisi field), tidak
            # writable lewat generic copy ini lagi. "document_id" yang
            # jadi canonical relation dicopy sebagai gantinya.
            "document_id",
            "delivery_type_id",
            "commodity_id",
        ]

        vessel_details_fields = [
            "principle_agent_id", "shipping_agent_id", "scn_code", "warehouse_id",
            "smk_code1", "smk_code2", "close_date", "cargo_receipt_date",
            "stuffing_date", "contact_id", "yard_id", "depot_id", "depot_code", "depot_address",
            "depot_instruction", "general_instruction",
        ]
        
        shipment_info_fields = [
            # Shipment Info fields (only those in the view)
            "place_of_receipt_id", "place_of_delivery_id",
            "port_of_loading_id", "port_of_discharge_id", "via_port_id",
            "terminal_id", "feeder_vessel_id", "feeder_voyage_no",
            "mother_vessel_id", "mother_voyage_no", "shipping_line_id",
            "shipping_line_ref_no", "coloader_id", "coloader_ref_no",
            
            # Dates
            "etd", "eta", "eta_jkt",
        ]
        
        bl_info_fields = [
            "shipper_id", "consignee_id", "notify_party_id", "notify_same_as_consignee",
            "delivery_agent_id",
        ]

        hbl_update = {}
        for field in header_fields + bl_info_fields + vessel_details_fields + shipment_info_fields:
            if not hbl[field] and booking[field]:
                val = booking[field]
                hbl_update[field] = val.id if hasattr(val, 'id') else val
                
        # Explicitly map customer reference (booking: customer_reference -> hbl: customer_ref)
        if not hbl.customer_ref and booking.customer_reference:
            hbl_update['customer_ref'] = booking.customer_reference

        # Explicitly map routing fields
        if not hbl.from_city and booking.from_city:
            hbl_update['from_city'] = booking.from_city.id
        if not hbl.origin_country_id and booking.origin_country_id:
            hbl_update['origin_country_id'] = booking.origin_country_id.id
        if not hbl.to_city and booking.to_city:
            hbl_update['to_city'] = booking.to_city.id
        if not hbl.destination_country_id and booking.destination_country_id:
            hbl_update['destination_country_id'] = booking.destination_country_id.id

        if hbl_update:
            hbl.write(hbl_update)

        # FF-73 UAT fix (Bug 3): compatibility mirror TIDAK boleh lagi
        # bergantung pada "if not hbl.sale_order_ids" -- setelah FF-73, HBL
        # bisa saja sudah punya mirror sebagian (root A) sebelum Booking
        # -> Jobsheet ini dijalankan, sehingga guard kosong itu membuat
        # variant lain (B, dan C yang dibuat belakangan) tidak pernah
        # tersinkronkan. Root/anchor commercial group-nya adalah Booking
        # (source_quotation_id + variant_ids), bukan snapshot hbl.sale_order_ids
        # -- sinkronkan lewat shared FF-73 mirror sync (sale.order
        # _sync_sale_order_ids_mirror), dipanggil untuk setiap anggota
        # commercial group supaya Booking & Jobsheet canonical konsisten.
        root = booking._get_source_quotation()
        if root:
            for order in root | root.variant_ids:
                order._sync_sale_order_ids_mirror()

        if not hbl.cargo_info_ids and booking.cargo_info_ids:
            self._copy_cargo_info_lines_to_hbl(booking.cargo_info_ids, hbl)

        if not hbl.purchase_order_ids and booking.purchase_order_ids:
            hbl.write({"purchase_order_ids": [(6, 0, booking.purchase_order_ids.ids)]})

    def action_create_job(self):
        """FF-75: Booking Export -> Create Job. Membuat 1 Master Job (kalau
        belum ada) dan House Job PERTAMA otomatis dari
        Booking.source_quotation_id, langsung ter-gabung ke Master tersebut.
        Idempotent: dipanggil ulang tidak membuat Master/House kedua."""
        self.ensure_one()

        master = self.env["freight.sea.job"].search(
            [("booking_id", "=", self.id), ("record_level", "=", "master")],
            limit=1,
            order="id desc",
        )
        if not master:
            master = self.env["freight.sea.job"].create(
                {
                    "booking_id": self.id,
                    "record_level": "master",
                    "freight_type": self.freight_type,
                    "ship_mode": self.ship_mode,
                    # FF-79: copy sekali saat create -- setelah ini Booking
                    # dan Job TIDAK live-sync, job_type_id Job independen
                    # dan boleh diubah manual (Change Job Type) tanpa
                    # mempengaruhi Booking.
                    "job_type_id": self.job_type_id.id if self.job_type_id else False,
                    # FF-76 Step 2: Master harus memakai transport document
                    # yang EXACT sama dengan Booking (legal chain exception),
                    # atau kosong kalau Booking belum punya B/L (late
                    # assignment lewat Master, lihat freight.sea.job.write()).
                    "document_id": self.document_id.id if self.document_id else False,
                    "commodity_id": self.commodity_id.id if self.commodity_id else False,
                    "delivery_type_id": self.delivery_type_id.id if self.delivery_type_id else False,
                    # FF-75 follow-up (Section E): Master TIDAK boleh
                    # mengambil Customer dari Booking secara otomatis --
                    # semantic Customer Master consolidation belum
                    # dipastikan. customer_id Master tetap optional/False
                    # kecuali diisi eksplisit oleh user lewat flow lain.
                    "customer_ref": self.customer_reference,
                    "shipper_id": self.shipper_id.id if self.shipper_id else False,
                    "consignee_id": self.consignee_id.id if self.consignee_id else False,
                    "notify_party_id": self.notify_party_id.id if self.notify_party_id else False,
                    "notify_same_as_consignee": self.notify_same_as_consignee,
                    "delivery_agent_id": self.delivery_agent_id.id if self.delivery_agent_id else False,
                    "term_payment": self.payment_term_id.id,
                    "job_date": self.job_date,
                    "user_id": self.user_id.id if self.user_id else False,
                    "from_city": self.from_city.id if self.from_city else False,
                    "origin_country_id": self.origin_country_id.id if self.origin_country_id else False,
                    "to_city": self.to_city.id if self.to_city else False,
                    "destination_country_id": self.destination_country_id.id if self.destination_country_id else False,
                    "eta_jkt": self.eta_jkt,
                    "etd": self.etd,
                    "eta": self.eta,
                }
            )

        self._copy_booking_data_to_hbl(self, master)

        # House pertama otomatis dari source_quotation_id Booking (FF-75) --
        # hanya kalau Master belum punya House sama sekali (idempotent) dan
        # Booking punya source_quotation_id untuk diprefill.
        if not master.house_job_ids and self.source_quotation_id:
            house_vals = self.env["freight.sea.job"]._prepare_house_vals_from_quotation(
                self.source_quotation_id, master=master
            )
            self.env["freight.sea.job"].create(house_vals)

        return {
            "type": "ir.actions.act_window",
            "name": "Sea Job",
            "res_model": "freight.sea.job",
            "res_id": master.id,
            "view_mode": "form",
            "target": "current",
        }