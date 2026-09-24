import base64
import os

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.modules.module import get_module_resource


class FreightQuotation(models.AbstractModel):
    """
    Abstract mixin untuk semua jenis Quotation (Sea, Air, dll).
    Berisi field dan method yang sama di semua jenis quotation.

    Subclass WAJIB mendefinisikan:
        _quotation_table = "nama_tabel_db"        (str)
        _SALE_ORDER_SYNC_COLUMNS = (...)          (tuple of str)
    """

    _name = "freight.quotation"
    _description = "Freight Quotation Mixin"

    is_freight_quotation = fields.Boolean(string="Is Freight Quotation", default=False)

    # =========================================================
    # Header Information
    # =========================================================

    # Left side header
    freight_business_type = fields.Selection(
        selection=[
            ("sea", "Sea"),
            ("air", "Air"),
        ],
        string="Freight Business Type",
    )
    freight_type = fields.Selection(
        selection=[
            ("export", "Export"),
            ("import", "Import"),
        ],
        string="Quotation Type",
    )
    quotation_title = fields.Char(string="Quotation Title")
    contact_person = fields.Char(
        string="Contact Person",
        compute="_compute_contact_person",
        store=False,
    )
    partner_id = fields.Many2one("res.partner", string="Customer")
    phone = fields.Char(related="partner_id.phone", string="Phone", readonly=True)
    email = fields.Char(related="partner_id.email", string="Email", readonly=True)

    service_level = fields.Selection(
        [("p1", "P1"), ("p2", "P2"), ("p3", "P3"), ("p4", "P4")],
        string="Service Level",
        default=False,
    )

    # Right side header
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist")
    delivery_type_id = fields.Many2one(
        "account.incoterms", string="Delivery Type"
    )
    valid_from = fields.Date(string="Valid From")
    # validity_date = fields.Date(string="Valid To")
    reference_number = fields.Char(string="Reference Number")
    commodity_id = fields.Many2one(
        "freight.commodity", string="Commodity"
    )

    # Address — Source
    pickup_street = fields.Char(string="Pickup Street")
    pickup_street2 = fields.Char(string="Pickup  Street 2")
    pickup_city = fields.Many2one("res.city", string="Pickup  City")
    pickup_state_id = fields.Many2one("res.country.state", string="Pickup  State")
    pickup_zip = fields.Char(string="Pickup  Zip")
    pickup_country_id = fields.Many2one("res.country", string="Pickup  Country")

    # Address — Destination
    delivery_street = fields.Char(string="Delivery Street")
    delivery_street2 = fields.Char(string="Delivery Street 2")
    delivery_city = fields.Many2one("res.city", string="Delivery City")
    delivery_state_id = fields.Many2one("res.country.state", string="Delivery State")
    delivery_zip = fields.Char(string="Delivery Zip")
    delivery_country_id = fields.Many2one("res.country", string="Delivery Country")

    @api.onchange("pickup_city")
    def _onchange_pickup_city(self):
        city = self.pickup_city
        if not city:
            return
        if city.zipcode:
            self.pickup_zip = city.zipcode
        if city.state_id:
            self.pickup_state_id = city.state_id
        if city.country_id:
            self.pickup_country_id = city.country_id

    @api.onchange("delivery_city")
    def _onchange_delivery_city(self):
        city = self.delivery_city
        if not city:
            return
        if city.zipcode:
            self.delivery_zip = city.zipcode
        if city.state_id:
            self.delivery_state_id = city.state_id
        if city.country_id:
            self.delivery_country_id = city.country_id

    # Extra Info
    description_of_goods = fields.Char(string="Description of Goods")
    quantity = fields.Integer(string="Quantity")
    actual_weight = fields.Float(string="Actual Weight (Kg)")
    volume = fields.Float(string="Volume (Kg)")
    chargeable_weight = fields.Float(string="Chargeable Weight (Kg)")
    has_insurance = fields.Boolean(string="Has Insurance")
    insurance_id = fields.Many2one("freight.insurance", string="Insurance")

    # Dimension
    loose_quantity = fields.Integer(string="Loose Quantity")
    pcs = fields.Integer(string="PCS")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")
    dimension = fields.Float(string="Dimension")

    # Shipment Info — Common
    origin_id = fields.Many2one("res.city", string="Origin")
    destination_id = fields.Many2one("res.city", string="Destination")

    # =========================================================
    # FF-81: Freight Charge header -- Pricelist (Charge Table) eligibility
    # =========================================================

    # Business reference date untuk eligibility Pricelist (Charge Table) --
    # berdiri sendiri, SENGAJA tidak di-derive dari valid_from/date_order/
    # create_date (lihat FF-81 koreksi). Source date ini bisa berubah
    # setelah UAT/business confirmation lebih lanjut.
    pricing_date = fields.Date(
        string="Pricing Date",
        default=fields.Date.context_today,
    )

    eligible_pricelist_ids = fields.Many2many(
        "product.pricelist",
        compute="_compute_eligible_pricelist_ids",
        string="Eligible Charge Tables",
    )

    @api.depends(
        "is_freight_quotation", "freight_business_type", "freight_type",
        "partner_id", "destination_id", "pricing_date",
        "port_of_loading_id", "port_of_discharge_id", "via_port_id", "sea_ship_mode",
        "airport_of_origin_id", "airport_of_destination_id", "via_airport_id",
    )
    def _compute_eligible_pricelist_ids(self):
        """FF-81: `port_of_loading_id`/`sea_ship_mode`/`airport_of_*_id` are
        defined in the Sea/Air submodules (models/sea|air/sales/quotation.py),
        not on this abstract mixin -- but since both submodules target the
        SAME final model (sale.order), every sale.order record carries every
        one of these columns regardless of business type, so depending on
        them here is safe (mirrors the hasattr()-based cross-domain access
        already used elsewhere in this file, e.g. _get_freight_job)."""
        for rec in self:
            rec.eligible_pricelist_ids = (
                rec._get_eligible_pricelists() if rec.is_freight_quotation
                else self.env["product.pricelist"]
            )

    @api.onchange(
        "partner_id", "freight_business_type", "freight_type", "destination_id",
        "pricing_date", "port_of_loading_id", "port_of_discharge_id", "via_port_id",
        "sea_ship_mode", "airport_of_origin_id", "airport_of_destination_id", "via_airport_id",
    )
    def _onchange_ff_pricelist_eligibility(self):
        """FF-81: Freight Charge header context berubah -> Pricelist yang
        sedang dipilih tapi sudah tidak eligible (mismatch Customer/route/
        Job Type/tanggal) dikosongkan lagi, bukan dibiarkan diam-diam
        menunjuk Charge Table yang sudah tidak cocok."""
        for rec in self:
            if not rec.is_freight_quotation or not rec.pricelist_id:
                continue
            if rec.pricelist_id not in rec._get_eligible_pricelists():
                rec.pricelist_id = False

    def _ff_pricelist_route_domain_fields(self):
        """FF-81: (Charge Table header field, quotation value) pairs untuk
        dimensi route yang relevan dengan `freight_business_type` quotation
        ini -- Sea pakai Port fields, Air pakai Airport fields; field yang
        tidak relevan untuk business_type lain tidak pernah ikut jadi
        kriteria (lihat ff_type strict di `_get_eligible_pricelist_domain`)."""
        self.ensure_one()
        if self.freight_business_type == "sea":
            return [
                ("ff_port_of_loading_id", self.port_of_loading_id.id),
                ("ff_port_of_discharge_id", self.port_of_discharge_id.id),
                ("ff_via_port_id", self.via_port_id.id),
            ]
        if self.freight_business_type == "air":
            return [
                ("ff_airport_of_origin_id", self.airport_of_origin_id.id),
                ("ff_airport_of_destination_id", self.airport_of_destination_id.id),
                ("ff_via_airport_id", self.via_airport_id.id),
            ]
        return []

    def _get_pricelist_job_type_candidate(self):
        """FF-81: resolve kandidat Job Type untuk eligibility Pricelist,
        REUSE resolver classification yang sama dengan
        `freight.job.type.resolver.mixin` (business_type/freight_type/
        sea_ship_mode) -- bukan formula/matching terpisah berdasarkan
        code/name Job Type.

        Cardinality klasifikasi->Job Type TIDAK diasumsikan 1:1: hanya
        dikembalikan kalau resolusinya benar-benar tunggal (tepat 1
        kandidat aktif). Kalau 0 atau >1 kandidat (ambiguous/unresolved),
        dikembalikan recordset kosong -- caller
        (`_get_eligible_pricelist_domain`) TIDAK PERNAH menebak salah satu
        kandidat: lihat `_ff_job_type_eligibility_value` untuk bagaimana
        hasil kosong ini diterjemahkan ke filtering (strict, BUKAN skip)."""
        self.ensure_one()
        business_type = self.freight_business_type
        sea_ship_mode = self.sea_ship_mode if business_type == "sea" else False
        candidates = self.env["freight.job.type"]._get_matching_job_types(
            business_type, self.freight_type, sea_ship_mode
        )
        return candidates if len(candidates) == 1 else self.env["freight.job.type"]

    def _ff_job_type_eligibility_value(self):
        """FF-81 koreksi: rule wildcard-or-exact-match yang sama dengan
        dimensi lain (Customer/route/dst.) HARUS berlaku juga untuk Job
        Type -- termasuk saat resolver ambiguous/unresolved (0 atau >1
        kandidat).

        - Resolver tunggal (tepat 1 kandidat) -> Charge Table dengan
          ff_job_type_id kosong ATAU sama dengan kandidat itu eligible.
        - Resolver ambiguous/unresolved (0 atau >1 kandidat) -> HANYA
          Charge Table dengan ff_job_type_id kosong yang eligible; Charge
          Table Job-Type-specific manapun (apa pun isinya) TIDAK eligible,
          karena quotation tidak bisa membuktikan exact match-nya. Ini
          BUKAN skip filtering (perilaku lama, terlalu permisif) dan BUKAN
          menebak salah satu kandidat."""
        self.ensure_one()
        job_type = self._get_pricelist_job_type_candidate()
        return job_type.id if job_type else False

    def _get_eligible_pricelist_domain(self):
        """FF-81: domain eligibility Pricelist (Charge Table) untuk konteks
        Freight Charge header quotation ini.

        - ff_type strict: Sea quotation hanya melihat Charge Table
          ff_type='sea', Air hanya 'air'.
        - Setiap field header FF lain (termasuk Job Type): wildcard-or-
          exact-match -- Charge Table field kosong = wildcard (selalu
          match), field terisi wajib exact match ke field quotation yang
          bersangkutan (Job Type ambiguous/unresolved diperlakukan sebagai
          TIDAK BISA membuktikan match, lihat `_ff_job_type_eligibility_value`).
        - Validity date pakai `pricing_date` (business reference date
          berdiri sendiri -- BUKAN valid_from/date_order/create_date).
        - Hanya Charge Table `active=True` yang eligible; field TBD (FF-81
          "Field only" list) TIDAK PERNAH ikut jadi kriteria di sini.
        """
        self.ensure_one()
        if not self.is_freight_quotation or self.freight_business_type not in ("sea", "air"):
            return [("id", "=", False)]

        domain = [("active", "=", True), ("ff_type", "=", self.freight_business_type)]

        def _wildcard_or_match(field_name, value):
            domain.extend(["|", (field_name, "=", False), (field_name, "=", value or False)])

        _wildcard_or_match("ff_customer_id", self.partner_id.id)
        if self.freight_business_type == "sea":
            _wildcard_or_match("ff_destination_city_id", self.destination_id.id)
        for field_name, value in self._ff_pricelist_route_domain_fields():
            _wildcard_or_match(field_name, value)

        _wildcard_or_match("ff_job_type_id", self._ff_job_type_eligibility_value())

        check_date = self.pricing_date or fields.Date.context_today(self)
        domain.extend([
            "|", ("ff_effective_date", "=", False), ("ff_effective_date", "<=", check_date),
            "|", ("ff_expiry_date", "=", False), ("ff_expiry_date", ">=", check_date),
        ])
        return domain

    def _get_eligible_pricelists(self):
        self.ensure_one()
        return self.env["product.pricelist"].search(self._get_eligible_pricelist_domain())
    est_transit_time_days = fields.Integer(string="Est. Transit Time (Days)", default=0)
    est_transit_time_note = fields.Char(string="Est. Transit Time Note")
    frequency = fields.Selection(
        selection=[("weekly", "Weekly"), ("bi_weekly", "Bi-weekly")],
        string="Frequency",
    )
    frt_collect = fields.Selection(
        selection=[("Y", "Collect"), ("N", "Prepaid")],
        string="FRT Collect",
        default="N",
    )
    note = fields.Text(string="Note")

    # Header & Footer
    header = fields.Char(string="Header")
    special_instruction = fields.Text(string="Special Instruction")
    footer = fields.Char(string="Footer")

    # Terms and Condition
    terms_and_conditions = fields.Text(string="Terms & Conditions")

    # =========================================================
    # Common Methods
    # =========================================================

    def _compute_tasks_ids(self):
        for rec in self:
            rec.tasks_ids = False
            rec.tasks_count = 0
            rec.closed_task_count = 0

    @api.depends("partner_id.child_ids")
    def _compute_contact_person(self):
        for rec in self:
            children = (
                rec.partner_id.child_ids if rec.partner_id else self.env["res.partner"]
            )
            rec.contact_person = children[0].name if children else False

    @api.constrains("est_transit_time_days")
    def _check_est_transit_time_days(self):
        for record in self:
            if record.est_transit_time_days < 0:
                raise ValidationError("Est. Transit Time (Days) cannot be negative.")

    def _has_downstream_quotation_records(self):
        """True jika quotation ini sudah punya Booking/Jobsheet turunan
        (Sea maupun Air) — dipakai untuk mengunci perubahan direction."""
        self.ensure_one()
        return bool(
            self.booking_count
            or self.sea_job_count
            or getattr(self, "air_booking_count", 0)
            or getattr(self, "air_job_count", 0)
        )

    def action_convert_quotation(self):
        """Satu entry point publik untuk convert quotation ke downstream
        record; branching Import/Export ditangani di sini, bukan lewat
        dua button/action terpisah (lihat FF-71).

        FF-73 hardening: freight_type sekarang boleh kosong saat quotation
        cuma disimpan sebagai draft (cukup Customer) -- tapi Convert BUTUH
        tahu arah Import/Export secara eksplisit untuk menentukan cabang
        yang benar. Kosong TIDAK boleh diam-diam dianggap Export."""
        self.ensure_one()
        if not self.is_freight_quotation:
            raise UserError(
                "This action is only available for a Freight Quotation."
            )
        if not self.freight_type:
            raise UserError(
                "Quotation Type (Import/Export) must be set before converting this quotation."
            )
        if self.freight_type == "import":
            return self.action_convert_to_jobsheet_direct()
        return self.action_convert_to_booking_direct()

    def action_convert_to_booking_direct(self):
        """Dispatch eksplisit berdasarkan freight_business_type, bukan
        lewat urutan _inherit/super() antar modul air & sea — supaya tidak
        diam-diam salah pilih implementasi kalau urutan import berubah.

        FF-73 hardening: freight_business_type boleh kosong saat draft,
        tapi convert butuh tahu Air/Sea secara eksplisit -- kosong/nilai
        lain TIDAK boleh diam-diam jatuh ke Sea.

        FF-73 UAT fix (Bug 1): guard di backend, bukan cuma visibility
        tombol -- kalau commercial group (root + currency variant-nya) SUDAH
        punya Booking, panggil action ini dari variant mana pun (bukan cuma
        root) harus membuka Booking yang sudah ada, bukan diam-diam membuat
        Booking kedua untuk commercial group yang sama."""
        self.ensure_one()
        if self.freight_business_type == "air":
            booking_model = "freight.air.booking"
        elif self.freight_business_type == "sea":
            booking_model = "freight.sea.booking"
        else:
            raise UserError(
                "Freight Business Type (Air/Sea) must be set before converting this quotation to a Booking."
            )
        existing = self._get_commercial_group_bookings(booking_model)
        if existing:
            return {
                "type": "ir.actions.act_window",
                "res_model": booking_model,
                "res_id": existing[0].id,
                "view_mode": "form",
                "target": "current",
            }
        if booking_model == "freight.air.booking":
            return self._action_convert_to_booking_direct_air()
        return self._action_convert_to_booking_direct_sea()

    def action_convert_to_jobsheet_direct(self):
        """Dispatch eksplisit berdasarkan freight_business_type — lihat
        action_convert_to_booking_direct."""
        self.ensure_one()
        if self.freight_business_type == "air":
            return self._action_convert_to_jobsheet_direct_air()
        if self.freight_business_type == "sea":
            return self._action_convert_to_jobsheet_direct_sea()
        raise UserError(
            "Freight Business Type (Air/Sea) must be set before converting this quotation to a Jobsheet."
        )

    def _sync_sale_order_rows(self):
        """
        Sync baris dari tabel quotation masing-masing ke sale_order.
        Subclass wajib mendefinisikan _quotation_table dan _SALE_ORDER_SYNC_COLUMNS.

        Catatan arsitektur: menggunakan raw SQL (bukan ORM) karena sale_order
        adalah tabel Odoo bawaan yang tidak bisa di-inherit secara langsung.
        Setelah raw INSERT, cache ORM di-invalidate secara eksplisit.
        """
        if self._name == "sale.order":
            return
        ids = self.ids
        query_filter = ""
        params = []
        if ids:
            query_filter = "WHERE q.id = ANY(%s)"
            params.append(ids)

        table = self._quotation_table
        columns = ", ".join(self._SALE_ORDER_SYNC_COLUMNS)
        select_columns = ", ".join(
            f"q.{column}" for column in self._SALE_ORDER_SYNC_COLUMNS
        )
        update_columns = ", ".join(
            f"{column} = EXCLUDED.{column}" for column in self._SALE_ORDER_SYNC_COLUMNS
        )

        self.env.cr.execute(
            f"""
            INSERT INTO sale_order (id, {columns})
            SELECT q.id, {select_columns}
            FROM {table} q
            {query_filter}
            ON CONFLICT (id)
            DO UPDATE SET {update_columns}
            """,
            params,
        )
        self.env.cr.execute(
            """
            SELECT setval(
                'sale_order_id_seq',
                (SELECT COALESCE(MAX(id), 1) FROM sale_order),
                TRUE
            )
            """
        )

        # Perbaiki issue currency di order_line (sale.order.line)
        # Karena INSERT/UPDATE ke sale_order di atas menggunakan raw SQL,
        # ORM tidak mendeteksi perubahan dan tidak me-recompute related field (currency_id) di line.
        # Kita update langsung di DB agar sinkron.
        if ids:
            self.env.cr.execute(
                """
                UPDATE sale_order_line sol
                SET currency_id = so.currency_id
                FROM sale_order so
                WHERE sol.order_id = so.id 
                  AND so.id = ANY(%s) 
                  AND (sol.currency_id != so.currency_id OR sol.currency_id IS NULL)
                """,
                [ids],
            )

        # Invalidate ORM cache agar data yang baru di-sync terbaca dengan benar
        self.env["sale.order"].invalidate_model()
        self.env["sale.order.line"].invalidate_model(["currency_id"])

    def copy(self, default=None):
        """
        Override copy() untuk:
        1. Preserve validity_date (Expiry Date) dari record sumber.
           Tanpa ini, saat duplicate Odoo me-reset date_order ke hari ini
           sehingga validity_date ikut recalculate → beda dari aslinya.
        2. Menyelesaikan issue "Missing Record" saat menduplikasi order_line.
           Karena order_line divalidasi ke tabel sale_order, kita menunda
           duplikasi order_line sampai setelah record disinkronisasi ke sale_order.
        """
        if self._name == "sale.order":
            return super().copy(default=default)
            
        default = dict(default or {})
        # Salin validity_date dari source agar tidak di-recalculate
        if "validity_date" not in default and self.validity_date:
            default["validity_date"] = self.validity_date

        # Tunda duplikasi order_line dari ORM bawaan
        copy_order_lines = False
        if "order_line" not in default:
            default["order_line"] = False
            copy_order_lines = True
        elif not default["order_line"]:
            # [] atau None dari caller (misal action_create_currency_variant) tidak cukup untuk
            # suppress copying di Odoo ORM — normalize ke False agar lines tidak ikut ter-copy.
            default["order_line"] = False

        new_record = super().copy(default=default)
        new_record._sync_sale_order_rows()

        # Setelah record disinkronisasi ke tabel sale_order, barulah aman menduplikasi order_line
        if copy_order_lines and self.order_line:
            for line in self.order_line:
                line.copy({"order_id": new_record.id})

        return new_record

    @api.model_create_multi
    def create(self, vals_list):
        if self._name == "sale.order":
            return super().create(vals_list)
        records = super().create(vals_list)
        # Flush deferred computed fields (e.g. currency_id dari pricelist_id) ke DB
        # sebelum raw SQL sync, agar _sync_sale_order_rows tidak baca nilai stale.
        records.flush_recordset()
        records._sync_sale_order_rows()
        return records

    def write(self, vals):
        if "freight_type" in vals:
            for rec in self:
                if (
                    rec.is_freight_quotation
                    and rec.freight_type
                    and vals["freight_type"] != rec.freight_type
                    and rec._has_downstream_quotation_records()
                ):
                    raise UserError(
                        "Quotation Type (Import/Export) cannot be changed anymore: "
                        "this quotation already has a Booking or Jobsheet linked to it."
                    )
        if self._name == "sale.order":
            return super().write(vals)
        result = super().write(vals)
        # Flush deferred computed fields sebelum sync — lihat FF-19.
        self.flush_recordset()
        self._sync_sale_order_rows()
        return result

    def unlink(self):
        if self._name == "sale.order":
            return super().unlink()
        ids = self.ids
        result = super().unlink()
        if ids:
            self.env.cr.execute("DELETE FROM sale_order WHERE id = ANY(%s)", [ids])
            # Invalidate cache setelah raw DELETE
            self.env["sale.order"].invalidate_model()
        return result

    def _get_sea_job_analytic_account(self):
        """FF-73: fallback resolve lewat commercial group (root + variant),
        bukan cuma sale_order_ids milik diri sendiri -- supaya currency
        variant yang dibuat SETELAH Jobsheet ada tetap kebagian analytic
        account tanpa perlu ditambahkan manual ke tab Sales Orders Jobsheet.

        Kalau commercial group resolve ke LEBIH DARI SATU Jobsheet (data
        ambigu), sengaja tidak auto-pilih salah satu -- lebih baik tidak
        mengisi analytic_distribution sama sekali daripada menebak."""
        self.ensure_one()
        if hasattr(self, "sea_job_id") and self.sea_job_id and self.sea_job_id.analytic_account_id:
            return self.sea_job_id.analytic_account_id
        hbls = self._get_commercial_group_jobsheets("freight.sea.job")
        if len(hbls) == 1 and hbls.analytic_account_id:
            return hbls.analytic_account_id
        if self.env.context.get("default_sea_job_id"):
            hbl = self.env["freight.sea.job"].browse(self.env.context.get("default_sea_job_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    def _get_air_job_analytic_account(self):
        """Mirror _get_sea_job_analytic_account untuk Air -- FF-73, menutup
        gap yang sebelumnya cuma ada di sisi Sea (Follow-up B)."""
        self.ensure_one()
        if hasattr(self, "air_job_id") and self.air_job_id and self.air_job_id.analytic_account_id:
            return self.air_job_id.analytic_account_id
        hawbs = self._get_commercial_group_jobsheets("freight.air.job")
        if len(hawbs) == 1 and hawbs.analytic_account_id:
            return hawbs.analytic_account_id
        if self.env.context.get("default_air_job_id"):
            hawb = self.env["freight.air.job"].browse(self.env.context.get("default_air_job_id"))
            if hawb and hawb.analytic_account_id:
                return hawb.analytic_account_id
        return False

    def _get_freight_job(self):
        """FF-79: resolve Sea/Air Job terkait quotation ini, dipakai untuk
        mengambil job_type_id (account mapping resolver) -- mirror strategi
        resolve yang sudah dipakai _get_sea_job_analytic_account/
        _get_air_job_analytic_account (sea_job_id/air_job_id langsung, atau
        commercial group kalau resolve ke tepat satu Jobsheet)."""
        self.ensure_one()
        if hasattr(self, "sea_job_id") and self.sea_job_id:
            return self.sea_job_id
        if hasattr(self, "air_job_id") and self.air_job_id:
            return self.air_job_id
        hbls = self._get_commercial_group_jobsheets("freight.sea.job")
        if len(hbls) == 1:
            return hbls
        hawbs = self._get_commercial_group_jobsheets("freight.air.job")
        if len(hawbs) == 1:
            return hawbs
        return self.env["freight.sea.job"]

    def _get_freight_job_type(self):
        job = self._get_freight_job()
        return job.job_type_id if job else self.env["freight.job.type"]

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if hasattr(self, "sea_job_id") and self.sea_job_id:
            invoice_vals["sea_job_id"] = self.sea_job_id.id
        else:
            hbl = self.env["freight.sea.job"].search([("sale_order_ids", "=", self.id)], limit=1)
            if hbl:
                invoice_vals["sea_job_id"] = hbl.id
        return invoice_vals

    def get_report_logo_src(self):
        logo_path = get_module_resource(
            "freight_forwarding", "static", "description", "logo.png"
        )
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return "data:image/png;base64," + encoded
        return ""


class SaleOrderQuotation(models.Model):
    """Satu-satunya tempat yang menempelkan mixin freight.quotation ke
    sale.order. SeaQuotation dan AirQuotation (models/sea|air/sales/quotation.py)
    sengaja hanya _inherit = "sale.order" (plain) — tidak ada satupun dari
    keduanya yang perlu tahu soal mixin ini (lihat FF-71 structural cleanup).

    Class ini juga menampung fitur currency-variant: generik, tidak menyentuh
    field sea-specific maupun air-specific apa pun, dan sudah dipakai oleh
    view Air maupun Sea.
    """

    _name = "sale.order"
    _inherit = ["sale.order", "freight.quotation"]

    # FF-73: model Booking/Jobsheet yang jadi anggota commercial group --
    # dipakai bersama oleh resolver analytic (Masalah 1), smart button
    # (Masalah 2), dan sync sale_order_ids mirror (Masalah 3).
    _COMMERCIAL_GROUP_BOOKING_MODELS = ("freight.sea.booking", "freight.air.booking")
    _COMMERCIAL_GROUP_JOBSHEET_MODELS = ("freight.sea.job", "freight.air.job")

    # FF-73 UAT fix (Masalah 2): field lokal di sale.order (kalau ada) yang
    # jadi compatibility mirror dari Booking/Jobsheet canonical -- parity
    # dengan air_booking_ids milik Air, yang sudah terbukti langsung fresh
    # di form browser (lewat copy() field inheritance + write eksplisit),
    # tanpa perlu reload. Air Jobsheet (air_job_id, Many2one) sengaja TIDAK
    # dimasukkan di sini -- cardinality-nya singular by design dan sudah
    # ditangani lifecycle Air sendiri (lihat AirQuotation), jangan disentuh.
    _COMMERCIAL_GROUP_LOCAL_MIRROR_FIELDS = {
        "freight.sea.booking": "booking_ids",
        "freight.sea.job": "sea_job_ids",
    }

    original_quotation_id = fields.Many2one(
        "sale.order",
        string="Original Quotation",
        copy=False,
        index=True,
    )
    variant_ids = fields.One2many(
        "sale.order",
        "original_quotation_id",
        string="Currency Variants",
    )
    variant_count = fields.Integer(
        string="Variant Count",
        compute="_compute_variant_count",
    )

    @api.depends("variant_ids", "original_quotation_id.variant_ids")
    def _compute_variant_count(self):
        for rec in self:
            root = rec.original_quotation_id if rec.original_quotation_id else rec
            rec.variant_count = len(root.variant_ids)

    def _get_commercial_group_jobsheets(self, jobsheet_model):
        """FF-75: resolve Job (freight.sea.job / freight.air.job) milik
        commercial group quotation ini.

        Canonical-first, legacy-fallback -- BUKAN union setara.
        source_quotation_id adalah source of truth: setiap Job (Master
        maupun House) menyimpan source-nya SENDIRI secara langsung saat
        dibuat (dari Booking.source_quotation_id untuk House pertama, dari
        Quotation aktif untuk Add-to-Master/Import) -- resolver ini SENGAJA
        tidak lagi ikut mengecek booking_id.source_quotation_id supaya tidak
        memaksa seluruh House di bawah satu Master/Booking mengikuti
        source_quotation_id yang sama (FF-75, House boleh punya commercial
        root sendiri-sendiri).

        1. Canonical: source_quotation_id langsung di Job.
        2. Fallback (hanya jika canonical kosong): sale_order_ids berisi
           salah satu anggota commercial group (root ATAU variant-nya --
           bukan cuma diri sendiri), untuk data lama yang belum di-backfill.
        """
        self.ensure_one()
        root = self.original_quotation_id or self
        canonical = self.env[jobsheet_model].search([("source_quotation_id", "=", root.id)])
        if canonical:
            return canonical
        group_ids = (root | root.variant_ids).ids
        return self.env[jobsheet_model].search([("sale_order_ids", "in", group_ids)])

    def _get_commercial_group_bookings(self, booking_model):
        """Sama seperti _get_commercial_group_jobsheets, untuk Booking
        (freight.sea.booking / freight.air.booking) -- Booking tidak punya
        booking_id sendiri, jadi canonical cukup source_quotation_id langsung.

        FF-73 UAT fix (Bug 1): canonical-first, legacy-fallback (sale_order_ids)
        sama seperti _get_commercial_group_jobsheets -- supaya Booking lama
        yang belum sempat di-backfill source_quotation_id-nya tetap resolve,
        dan supaya resolver ini (dipakai booking_count/action_view_bookings/
        guard duplicate conversion) tidak balik bergantung pada booking_ids/
        air_booking_ids milik record quotation yang sedang dibuka."""
        self.ensure_one()
        root = self.original_quotation_id or self
        canonical = self.env[booking_model].search([("source_quotation_id", "=", root.id)])
        if canonical:
            return canonical
        group_ids = (root | root.variant_ids).ids
        return self.env[booking_model].search([("sale_order_ids", "in", group_ids)])

    def _sync_sale_order_ids_mirror(self):
        """FF-73 Masalah 3: sale_order_ids pada Booking/Jobsheet tetap
        dipertahankan sebagai compatibility mirror untuk finance/analytic/
        invoice -- source_quotation_id + variant_ids tetap source of truth
        commercial group. Dipanggil setiap kali currency variant baru
        dibuat, supaya variant tersebut otomatis ikut tercermin di
        sale_order_ids Booking/Jobsheet yang sudah ada -- tidak lagi
        mengandalkan penambahan manual lewat tab Sales Orders."""
        self.ensure_one()
        for model in self._COMMERCIAL_GROUP_BOOKING_MODELS:
            found = self._get_commercial_group_bookings(model)
            for rec in found:
                if self.id not in rec.sale_order_ids.ids:
                    rec.sale_order_ids = [(4, self.id)]
            self._mirror_commercial_group_local_relation(model, found)
        for model in self._COMMERCIAL_GROUP_JOBSHEET_MODELS:
            found = self._get_commercial_group_jobsheets(model)
            for rec in found:
                if self.id not in rec.sale_order_ids.ids:
                    rec.sale_order_ids = [(4, self.id)]
            self._mirror_commercial_group_local_relation(model, found)
        self._invalidate_commercial_group_downstream_counts()

    def _mirror_commercial_group_local_relation(self, model, records):
        """FF-73 UAT fix (Masalah 2): selain menulis `self` ke sale_order_ids
        milik Booking/Jobsheet canonical (mirror arah Booking->SO di atas),
        tulis juga arah sebaliknya (SO->Booking) ke field lokal `self` kalau
        model tersebut punya compatibility mirror field (lihat
        _COMMERCIAL_GROUP_LOCAL_MIRROR_FIELDS) -- supaya `self.booking_ids` /
        `self.sea_job_ids` langsung merepresentasikan Booking/Jobsheet canonical
        yang sama, persis seperti `air_booking_ids` milik Air. Ini murni
        compatibility mirror; canonical resolver (source_quotation_id/
        booking_id) tetap tidak berubah dan tidak digantikan."""
        self.ensure_one()
        if not records:
            return
        mirror_field = self._COMMERCIAL_GROUP_LOCAL_MIRROR_FIELDS.get(model)
        if not mirror_field or not hasattr(self, mirror_field):
            return
        current = getattr(self, mirror_field)
        missing = records - current
        if missing:
            setattr(self, mirror_field, [(4, rec_id) for rec_id in missing.ids])

    _COMMERCIAL_GROUP_DOWNSTREAM_COUNT_FIELDS = (
        "booking_count", "sea_job_count", "air_booking_count", "air_job_count",
    )

    def _invalidate_commercial_group_downstream_counts(self):
        """FF-73 UAT fix (stale count): booking_count/sea_job_count/air_booking_count/
        air_job_count di sale.order dihitung lewat live search/relation lintas
        record (commercial group), tapi @api.depends-nya hanya mengacu ke
        field lokal record itu sendiri (mis. booking_ids, sea_job_id).
        Akibatnya, saat variant baru dibuat lalu _sync_sale_order_ids_mirror
        menulis sale_order_ids di Booking/Jobsheet milik member group LAIN,
        ORM tidak tahu compute value yang sudah ke-cache di record C
        (member yang baru) menjadi stale, karena tidak ada field ber-depends
        di C sendiri yang berubah.

        Fix-nya bukan mengubah resolver atau depends (itu tetap benar dan
        tidak disentuh) melainkan meng-invalidate cache compute field ini
        untuk seluruh anggota commercial group begitu sync selesai, supaya
        akses berikutnya (termasuk di request/form yang sama, tanpa reload)
        memicu recompute yang membaca ulang state ter-update lewat resolver
        yang sama."""
        self.ensure_one()
        root = self.original_quotation_id or self
        group = root | root.variant_ids
        group.invalidate_recordset(list(self._COMMERCIAL_GROUP_DOWNSTREAM_COUNT_FIELDS))

    @api.model_create_multi
    def create(self, vals_list):
        """FF-73 Masalah 3: integrity compatibility mirror TIDAK boleh
        bergantung pada action_create_currency_variant() -- record dengan
        original_quotation_id yang dibuat lewat jalur apa pun (ORM, API,
        test, migration, bukan cuma tombol Currency Variant) harus tetap
        otomatis mensinkronkan sale_order_ids Booking/Jobsheet terkait.
        original_quotation_id sengaja copy=False dan tidak pernah diisi
        lewat write() setelah creation (lihat action_create_currency_variant),
        jadi cukup ditangani di create() saja, tidak perlu di write()."""
        records = super().create(vals_list)
        for rec in records:
            if rec.original_quotation_id:
                rec._sync_sale_order_ids_mirror()
        return records

    def action_create_currency_variant(self):
        """
        Buat salinan header-only yang tertaut ke quotation asal sebagai currency variant.
        Berbeda dari Duplicate standar: tidak menyalin order lines,
        dan otomatis tertaut lewat original_quotation_id.
        """
        self.ensure_one()
        if not self.is_freight_quotation:
            raise UserError("This action is only available for Freight Quotations.")
        if self.original_quotation_id:
            raise UserError("You cannot create a currency variant from a child quotation. Please create it from the parent quotation instead.")

        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        # Sync sale_order_ids mirror (Masalah 3) ditangani di create() --
        # bukan di sini -- supaya integrity commercial group tidak bergantung
        # pada action ini (berlaku juga untuk pembuatan variant lewat ORM/API/test).
        new_variant = self.copy(default={
            'original_quotation_id': original_id,
            'order_line': [],
        })
        root = self.env["sale.order"].browse(original_id)
        form_view_id = self._get_freight_quotation_form_view_id(root.freight_business_type)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': new_variant.id,
            'view_mode': 'form',
            'views': [(form_view_id, "form")],
            'target': 'current',
        }

    # FF-73 UAT fix (Bug 2) mapping ini awalnya bernama _CURRENCY_VARIANT_FORM_VIEW_XMLID
    # dan hanya dipakai untuk currency variant. FF-66 UAT follow-up: dipakai juga oleh
    # Quote Info (action_open_freight_quotation_form) di luar konteks currency variant,
    # jadi di-rename generic -- satu-satunya tempat mapping Sea/Air form view didefinisikan.
    _FREIGHT_QUOTATION_FORM_VIEW_XMLID = {
        "air": "freight_forwarding.view_air_quotation_form",
        "sea": "freight_forwarding.view_sea_quotation_form",
    }

    def _get_freight_quotation_form_view_id(self, freight_business_type):
        """Satu mekanisme pemilihan form view Freight Quotation berdasarkan
        freight_business_type, dipakai oleh action_create_currency_variant(),
        action_view_currency_variants(), dan action_open_freight_quotation_form()
        -- supaya semuanya selalu konsisten (Sea/Air pakai form khusus, selain
        itu fallback ke False/default form)."""
        form_view_xmlid = self._FREIGHT_QUOTATION_FORM_VIEW_XMLID.get(freight_business_type)
        return self.env.ref(form_view_xmlid).id if form_view_xmlid else False

    def action_open_freight_quotation_form(self):
        """FF-66 UAT follow-up: dipanggil dari tombol Open di tab Quote Info
        milik res.partner. Embedded one2many (sale_order_ids) tidak bisa
        menentukan form_view_ref secara dinamis per row berdasarkan
        freight_business_type, jadi routing form dilakukan lewat action
        eksplisit ini alih-alih mengandalkan default form resolution
        sale.order.

        Freight Quotation (is_freight_quotation=True) dengan
        freight_business_type Sea/Air dibuka dengan form Freight yang sesuai.
        Record non-Freight / tanpa freight_business_type yang dikenal jatuh
        ke fallback aman: default sale.order form (tidak dipaksa pakai form
        Freight)."""
        self.ensure_one()
        form_view_id = False
        if self.is_freight_quotation:
            form_view_id = self._get_freight_quotation_form_view_id(self.freight_business_type)
        views = [(form_view_id, "form")] if form_view_id else [(False, "form")]
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.id,
            "view_mode": "form",
            "views": views,
            "target": "current",
        }

    def action_view_currency_variants(self):
        """FF-73 UAT fix (Bug 1): action ini dulu tidak menentukan form view
        sama sekali, sehingga Odoo jatuh ke default form sale.order (tanpa
        smart button Booking/Jobsheet Sea/Air) -- beda dengan dibuka lewat
        Quotation list yang sudah pakai view_sea_quotation_form/
        view_air_quotation_form (lihat action_freight_sea_quotation_view_form
        / action_freight_air_quotation_view_form). Sekarang eksplisit pilih
        form view yang sama berdasarkan freight_business_type root -- satu
        method common, tidak ada override terpisah di Sea/Air."""
        self.ensure_one()
        root = self.original_quotation_id if self.original_quotation_id else self
        domain = ['|', ('id', '=', root.id), ('original_quotation_id', '=', root.id)]

        form_view = (self._get_freight_quotation_form_view_id(root.freight_business_type), "form")

        return {
            "name": "Currency Variants",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "views": [(False, "list"), form_view],
            "domain": domain,
            "context": dict(self.env.context, create=False),
        }

    def action_confirm(self):
        res = super().action_confirm()
        for rec in self:
            if rec.is_freight_quotation:
                original_id = rec.original_quotation_id.id if rec.original_quotation_id else rec.id
                domain = [
                    '|', ('id', '=', original_id), ('original_quotation_id', '=', original_id),
                    ('id', '!=', rec.id),
                    ('state', 'in', ['draft', 'sent'])
                ]
                variants = self.env["sale.order"].search(domain)
                if variants:
                    # Prevent infinite recursion by passing context or just rely on state filter
                    variants.action_confirm()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_sea_job_analytic_account(self):
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_sea_job_analytic_account"):
            acc = self.order_id._get_sea_job_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_sea_job_id"):
            hbl = self.env["freight.sea.job"].browse(self.env.context.get("default_sea_job_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    def _get_air_job_analytic_account(self):
        """Mirror _get_sea_job_analytic_account untuk Air -- FF-73."""
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_air_job_analytic_account"):
            acc = self.order_id._get_air_job_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_air_job_id"):
            hawb = self.env["freight.air.job"].browse(self.env.context.get("default_air_job_id"))
            if hawb and hawb.analytic_account_id:
                return hawb.analytic_account_id
        return False

    def _get_freight_analytic_account(self):
        return self._get_sea_job_analytic_account() or self._get_air_job_analytic_account()

    def _get_freight_job_type(self):
        """FF-79: Job Type dari Jobsheet terkait order ini, dipakai resolve
        Sales Account mapping (Product/Charge Code x Job Type)."""
        if self.order_id and hasattr(self.order_id, "_get_freight_job_type"):
            return self.order_id._get_freight_job_type()
        return self.env["freight.job.type"]

    def _ff_resolve_billable_qty(self):
        """FF-82: (has_value, billable_qty) for this line, from the linked
        Job's operational data via the Charge Unit resolver, then Charge
        Code Minimum Billable Qty. `has_value=False` means the Charge Code
        has no Charge Unit, no Job is resolvable, or the Charge Unit has no
        confirmed formula yet -- caller must leave quantity untouched.

        Deliberately NOT stored/cached on `product_uom_qty` -- FF-82 requires
        Job actual qty / quoted qty / billable qty to stay three distinct
        numbers."""
        self.ensure_one()
        product_tmpl = self.product_id.product_tmpl_id if self.product_id else False
        charge_unit = product_tmpl.cc_charge_unit if product_tmpl else False
        if not charge_unit:
            return False, 0.0
        job = self.order_id._get_freight_job() if self.order_id else False
        if not job:
            return False, 0.0
        actual_qty = self.env["freight.charge.quantity.resolver"]._ff_resolve_actual_qty(job, charge_unit)
        if actual_qty is None:
            return False, 0.0
        min_qty = product_tmpl.cc_min_billable_qty or 0.0
        billable_qty = max(actual_qty, min_qty) if min_qty else actual_qty
        return True, billable_qty

    ff_billable_qty = fields.Float(
        string="FF Billable Qty",
        compute="_compute_ff_billable_qty",
        digits="Product Unit of Measure",
        help="FF-82: quantity resolved from Job operational data (Charge Unit) "
             "with Minimum Billable Qty applied. Falls back to the quoted "
             "quantity when the Charge Unit has no confirmed formula yet.",
    )

    @api.depends(
        "product_id",
        "product_id.product_tmpl_id.cc_charge_unit",
        "product_id.product_tmpl_id.cc_min_billable_qty",
        "order_id.sea_job_id",
        "order_id.air_job_id",
    )
    def _compute_ff_billable_qty(self):
        for line in self:
            has_value, qty = line._ff_resolve_billable_qty()
            line.ff_billable_qty = qty if has_value else line.product_uom_qty

    # FF-82 fix: override the native stored qty_to_invoice compute (instead
    # of patching account.move.line quantity in _prepare_invoice_line) so
    # remaining-to-invoice semantics stay correct across partial/multiple
    # invoices -- remaining_billable_qty = ff_billable_qty - qty_invoiced,
    # same depends as _compute_ff_billable_qty above (plus native
    # qty_invoiced/state, already covered by the base compute this extends).
    @api.depends(
        "product_id.product_tmpl_id.cc_charge_unit",
        "product_id.product_tmpl_id.cc_min_billable_qty",
        "order_id.sea_job_id",
        "order_id.air_job_id",
    )
    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        for line in self:
            if line.state != "sale" or line.display_type:
                continue
            has_billable_qty, billable_qty = line._ff_resolve_billable_qty()
            if has_billable_qty:
                line.qty_to_invoice = billable_qty - line.qty_invoiced

    @api.depends("product_id", "order_id.sea_job_id", "order_id.air_job_id")
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if not line.analytic_distribution and line.display_type not in ("line_section", "line_note"):
                analytic_account = line._get_freight_analytic_account()
                if analytic_account:
                    line.analytic_distribution = {str(analytic_account.id): 100.0}

    def _prepare_invoice_line(self, **optional_values):
        # FF-82 fix: no direct quantity override here anymore -- native
        # _prepare_invoice_line() already sets 'quantity': self.qty_to_invoice,
        # and _compute_qty_to_invoice() above is what makes qty_to_invoice
        # reflect Billable Qty (remaining_billable_qty = ff_billable_qty -
        # qty_invoiced) for lines whose Charge Unit resolves. This keeps
        # partial/multiple-invoice remaining-to-invoice tracking correct.
        res = super()._prepare_invoice_line(**optional_values)
        if not res.get("analytic_distribution"):
            analytic_account = self._get_freight_analytic_account()
            if analytic_account:
                res["analytic_distribution"] = {str(analytic_account.id): 100.0}
        if self.product_id and self.product_id.product_tmpl_id:
            job_type = self._get_freight_job_type()
            if job_type:
                sales_account = self.env["freight.charge.code.account.mapping"]._resolve_account(
                    self.product_id.product_tmpl_id, job_type, "sales_account_id"
                )
                if sales_account:
                    res["account_id"] = sales_account.id
        return res

