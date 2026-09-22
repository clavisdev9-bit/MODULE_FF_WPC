from odoo import api, fields, models
from odoo.exceptions import UserError


class SeaQuotation(models.Model):
    _inherit = "sale.order"

    # =========================================================
    # Sea-specific Fields
    # =========================================================

    # Relasi booking & HBL
    # FF-73 follow-up (generic Duplicate fix): copy=False di keempat field
    # commercial-group mirror ini (booking_ids/sea_job_ids/sea_job_id, dan yang
    # setara di Air) sengaja ditambahkan. Tanpa ini, generic copy() (tombol
    # Duplicate) ikut menyalin relasi Booking/Jobsheet milik record SUMBER ke
    # record BARU yang independen (bukan currency variant) -- lalu
    # SeaQuotation.create() di bawah menuliskannya balik ke
    # Booking/HBL.sale_order_ids, dan constraint commercial-group mixin
    # (freight.commercial.group.mixin) menolaknya karena duplicate itu bukan
    # anggota commercial group manapun (original_quotation_id-nya False).
    # Currency variant (action_create_currency_variant) TIDAK bergantung pada
    # copy() untuk field-field ini -- ia disinkronkan eksplisit lewat
    # _sync_sale_order_ids_mirror()/_mirror_commercial_group_local_relation()
    # dan "all_variants.write(...)" di action convert, jadi copy=False di
    # sini tidak memengaruhi currency variant sama sekali.
    booking_ids = fields.Many2many(
        "freight.sea.booking",
        string="Sea Bookings",
        copy=False,
    )
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_booking_count"
    )
    sea_job_count = fields.Integer(
        string="Jobsheet Count", compute="_compute_hbl_count"
    )
    sea_job_id = fields.Many2one(
        "freight.sea.job",
        string="Sea Jobsheet",
        index=True,
        copy=False,
    )
    # FF-73 UAT fix (Masalah 2): compatibility mirror -- BUKAN canonical
    # source of truth (itu tetap source_quotation_id / booking_id / resolver
    # _get_commercial_group_jobsheets). sea_job_id (Many2one) sengaja tidak
    # dipaksa jadi mirror karena cardinality-nya tidak menjamin selalu 1:1;
    # sea_job_ids (Many2many) di sini murni supaya currency variant langsung
    # "mengenali" Jobsheet canonical lewat field lokal (parity dengan
    # air_booking_ids milik Air), tanpa mengubah semantik sea_job_id.
    sea_job_ids = fields.Many2many(
        "freight.sea.job",
        string="Sea Jobsheets (compatibility mirror)",
        copy=False,
    )

    # FF-75 follow-up: field ini dulu bernama `container_type`, tapi
    # semantic-nya sama persis dengan `ship_mode` milik Booking/Job
    # (fcl/lcl) -- direname jadi `sea_ship_mode` (technical name sea-specific
    # karena sale.order juga dipakai Air, dan `ship_mode` Air punya semantic
    # berbeda). Konversi ke Booking/Job: sea_ship_mode -> ship_mode.
    sea_ship_mode = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
        ],
        string="Ship Mode",
    )


    # Shipment Info — Sea-specific (port / shipping line)
    port_of_loading_id = fields.Many2one("freight.port", string="Port Of Loading")
    port_of_discharge_id = fields.Many2one("freight.port", string="Port Of Discharge")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    shipping_line_id = fields.Many2one(
        "res.partner",
        string="Shipping Line",
        domain="[('category_id.freight_role_code', '=', 'shipping_line')]",
    )
    via2_id = fields.Many2one("freight.port", string="Via2")
    via3_id = fields.Many2one("freight.port", string="Via3")

    # =========================================================
    # Sea-specific Compute Methods
    # =========================================================

    @api.depends("original_quotation_id", "booking_ids")
    def _compute_booking_count(self):
        """FF-73 UAT fix (Bug 1): resolve lewat commercial group (root +
        variant), bukan cuma booking_ids milik diri sendiri -- supaya child
        variant tetap menunjukkan Booking yang benar meski root-nya yang
        pertama kali dikonversi. Mirror _compute_hbl_count.

        `booking_ids` tetap dicantumkan di depends (bukan sebagai source of
        truth resolusi, resolvernya tetap _get_commercial_group_bookings) --
        murni supaya compute field non-stored ini ter-invalidate saat Booking
        baru dibuat. `sale_order_ids` pada freight.sea.booking dan
        `booking_ids` pada sale.order berbagi tabel relasi m2m yang sama
        (tidak ada explicit relation= di kedua field), jadi menulis salah
        satu otomatis mencerminkan yang lain -- tanpa depends ini,
        booking_count akan nyangkut di cache lama begitu compute pernah
        diakses sebelum Booking-nya dibuat."""
        for rec in self:
            rec.booking_count = len(rec._get_commercial_group_bookings("freight.sea.booking"))

    @api.depends("sea_job_id", "original_quotation_id", "sea_job_ids")
    def _compute_hbl_count(self):
        """FF-73: resolve lewat commercial group (root + variant), bukan
        cuma sea_job_id/sale_order_ids milik diri sendiri -- supaya smart
        button tetap menunjukkan Jobsheet yang benar dari currency variant
        mana pun dalam commercial group yang sama.

        `sea_job_ids` (compatibility mirror) sengaja dimasukkan ke depends --
        sama seperti `booking_ids` di _compute_booking_count -- murni
        sebagai trigger invalidasi cache compute non-stored ini, BUKAN
        sebagai sumber hasil (hasil tetap dari resolver di atas)."""
        for rec in self:
            rec.sea_job_count = len(rec._get_commercial_group_jobsheets("freight.sea.job"))

    # =========================================================
    # Sea-specific Actions
    # =========================================================

    def action_view_bookings(self):
        """FF-73 UAT fix (Bug 1): resolve lewat commercial group -- lihat
        _compute_booking_count."""
        self.ensure_one()
        bookings = self._get_commercial_group_bookings("freight.sea.booking")
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({"default_sale_order_ids": [self.id]})
        return {
            "name": "Sea Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "view_mode": "form" if len(bookings) == 1 else "list,form",
            "domain": [("id", "in", bookings.ids)],
            "res_id": bookings.id if len(bookings) == 1 else False,
            "context": ctx,
        }

    def action_view_sea_jobs(self):
        self.ensure_one()
        hbls = self._get_commercial_group_jobsheets("freight.sea.job")
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({"default_sale_order_ids": [self.id]})
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.job",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": ctx,
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if hasattr(rec, "sea_job_id") and rec.sea_job_id:
                if rec.id not in rec.sea_job_id.sale_order_ids.ids:
                    rec.sea_job_id.sale_order_ids = [(4, rec.id)]
        return records

    def write(self, vals):
        res = super().write(vals)
        if "sea_job_id" in vals:
            for rec in self:
                if hasattr(rec, "sea_job_id") and rec.sea_job_id and rec.id not in rec.sea_job_id.sale_order_ids.ids:
                    rec.sea_job_id.sale_order_ids = [(4, rec.id)]
        return res

    def _action_convert_to_booking_direct_sea(self):
        self.ensure_one()
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        all_variants = self.env["sale.order"].search(domain)
        
        destination_country = (
            self.delivery_country_id or self.delivery_city.country_id
        )
        origin_country = self.pickup_country_id or self.pickup_city.country_id
        booking_no = self.env["ir.sequence"].next_by_code("freight.sea.booking")
        booking_vals = {
            "name": booking_no,
            "sale_order_ids": [(6, 0, all_variants.ids)],
            "source_quotation_id": original_id,
            "partner_id": self.partner_id.id,
            "delivery_type_id": self.delivery_type_id.id,
            "port_of_loading_id": self.port_of_loading_id.id,
            "port_of_discharge_id": self.port_of_discharge_id.id,
            "destination_country_id": (
                destination_country.id if destination_country else False
            ),
            "origin_country_id": origin_country.id if origin_country else False,
            "from_city": self.pickup_city.id,
            "to_city": self.delivery_city.id,
            "payment_term_id": self.payment_term_id.id,
            "ship_mode": self.sea_ship_mode,
            "commodity_id": self.commodity_id.id,
            "service_level": self.service_level,
            "freight_type": self.freight_type,
            "booking_date": fields.Datetime.now(),
            "job_date": fields.Date.today(),
            "company_id": self.company_id.id,
        }
        booking = self.env["freight.sea.booking"].create(booking_vals)
        # FF-73 UAT fix (Masalah 2): mirror eksplisit ke field lokal
        # booking_ids -- parity dengan Air (_action_convert_to_booking_direct_air)
        # -- supaya A/B langsung "mengenali" Booking lewat field sendiri,
        # bukan cuma lewat resolver, dan supaya currency variant yang dibuat
        # BELAKANGAN dari root ini otomatis mewarisi field ini lewat copy().
        all_variants.write({"booking_ids": [(4, booking.id)]})
        return {
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "target": "current",
        }

    def _action_convert_to_jobsheet_direct_sea(self):
        """FF-75: Import quotation -> Create Job TANPA Booking. Membuat 1
        Master Job + 1 House Job pertama yang diprefill dari Quotation aktif,
        langsung ter-gabung (master_job_id) ke Master tersebut.

        Master DI SINI BUKAN container kosong -- ia adalah freight.sea.job
        penuh (operational fields, shipment info, costing, document list,
        parties, dst. sama seperti Master hasil flow Export) yang tetap bisa
        diisi/diedit normal oleh user lewat form yang sama. Hanya saja tidak
        ada Booking untuk menyalin data awal, jadi field operasionalnya
        dimulai kosong (selain freight_type/ship_mode/company_id/
        job_date) -- bukan berarti recordnya dibatasi jadi shell. Data
        customer/commercial TIDAK dipaksakan ke Master (semantic Customer
        Master consolidation belum dipastikan -- lihat customer_id optional
        di hbl.py) -- itu tetap milik House, sesuai mapping existing yang
        sudah punya source jelas."""
        self.ensure_one()

        master = self.env["freight.sea.job"].create({
            "record_level": "master",
            "freight_type": self.freight_type,
            "ship_mode": self.sea_ship_mode,
            "company_id": self.company_id.id,
            "job_date": fields.Date.today(),
        })
        house_vals = self.env["freight.sea.job"]._prepare_house_vals_from_quotation(
            self, master=master
        )
        house = self.env["freight.sea.job"].create(house_vals)

        all_variants = house.source_quotation_id | house.source_quotation_id.variant_ids
        all_variants.write({"sea_job_id": house.id})
        # FF-73 UAT fix (Masalah 2): mirror eksplisit ke field lokal
        # sea_job_ids (compatibility mirror, bukan pengganti sea_job_id) --
        # parity dengan booking_ids di atas / air_booking_ids milik Air.
        all_variants.write({"sea_job_ids": [(4, house.id)]})
        return {
            "type": "ir.actions.act_window",
            "name": "Sea Job",
            "res_model": "freight.sea.job",
            # Master dibuka (bukan House) -- konsisten dengan flow Export
            # (Create Job dari Booking juga membuka Master), dan Master
            # adalah operational Job penuh, bukan detail implementasi yang
            # disembunyikan. House tetap bisa diakses lewat tab House Jobs.
            "res_id": master.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_sea_add_to_master_wizard(self):
        """FF-75 follow-up (method collision fix): nama method di-prefix
        `sea_` -- SeaQuotation dan AirQuotation sama-sama _inherit=
        "sale.order", jadi nama method generik `action_open_add_to_master_wizard`
        di kedua file saling override (yang belakangan dimuat MENANG untuk
        SEMUA quotation, Sea maupun Air) -- tombol Sea bisa membuka wizard
        Air. 'Add to Master' -- Freight Actions Export. Membuat House Job
        baru dari Quotation aktif dan menggabungkannya ke Master Sea
        existing (dipilih lewat wizard), TANPA membuat Booking baru."""
        self.ensure_one()
        if self.freight_type != "export":
            raise UserError("Add to Master hanya berlaku untuk Quotation Export.")
        return {
            "type": "ir.actions.act_window",
            "name": "Add to Master",
            "res_model": "freight.sea.add.to.master.wizard",
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, default_quotation_id=self.id),
        }
