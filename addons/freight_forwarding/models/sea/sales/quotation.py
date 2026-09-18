from odoo import api, fields, models


class SeaQuotation(models.Model):
    _inherit = "sale.order"

    # =========================================================
    # Sea-specific Fields
    # =========================================================

    # Relasi booking & HBL
    # FF-73 follow-up (generic Duplicate fix): copy=False di keempat field
    # commercial-group mirror ini (booking_ids/hbl_ids/sea_hbl_id, dan yang
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
    hbl_count = fields.Integer(
        string="Jobsheet Count", compute="_compute_hbl_count"
    )
    sea_hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Sea Jobsheet",
        index=True,
        copy=False,
    )
    # FF-73 UAT fix (Masalah 2): compatibility mirror -- BUKAN canonical
    # source of truth (itu tetap root_quotation_id / booking_id / resolver
    # _get_commercial_group_jobsheets). sea_hbl_id (Many2one) sengaja tidak
    # dipaksa jadi mirror karena cardinality-nya tidak menjamin selalu 1:1;
    # hbl_ids (Many2many) di sini murni supaya currency variant langsung
    # "mengenali" Jobsheet canonical lewat field lokal (parity dengan
    # air_booking_ids milik Air), tanpa mengubah semantik sea_hbl_id.
    hbl_ids = fields.Many2many(
        "freight.sea.hbl",
        string="Sea Jobsheets (compatibility mirror)",
        copy=False,
    )

    # Container Type (sea-specific, juga di-sync ke sale_order)
    container_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Container Type",
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

    @api.depends("sea_hbl_id", "original_quotation_id", "hbl_ids")
    def _compute_hbl_count(self):
        """FF-73: resolve lewat commercial group (root + variant), bukan
        cuma sea_hbl_id/sale_order_ids milik diri sendiri -- supaya smart
        button tetap menunjukkan Jobsheet yang benar dari currency variant
        mana pun dalam commercial group yang sama.

        `hbl_ids` (compatibility mirror) sengaja dimasukkan ke depends --
        sama seperti `booking_ids` di _compute_booking_count -- murni
        sebagai trigger invalidasi cache compute non-stored ini, BUKAN
        sebagai sumber hasil (hasil tetap dari resolver di atas)."""
        for rec in self:
            rec.hbl_count = len(rec._get_commercial_group_jobsheets("freight.sea.hbl"))

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

    def action_view_hbls(self):
        self.ensure_one()
        hbls = self._get_commercial_group_jobsheets("freight.sea.hbl")
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({"default_sale_order_ids": [self.id]})
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": ctx,
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if hasattr(rec, "sea_hbl_id") and rec.sea_hbl_id:
                if rec.id not in rec.sea_hbl_id.sale_order_ids.ids:
                    rec.sea_hbl_id.sale_order_ids = [(4, rec.id)]
        return records

    def write(self, vals):
        res = super().write(vals)
        if "sea_hbl_id" in vals:
            for rec in self:
                if hasattr(rec, "sea_hbl_id") and rec.sea_hbl_id and rec.id not in rec.sea_hbl_id.sale_order_ids.ids:
                    rec.sea_hbl_id.sale_order_ids = [(4, rec.id)]
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
            "root_quotation_id": original_id,
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
            "salesman_id": self.salesman_id.id,
            "payment_term_id": self.payment_term_id.id,
            "container_type": self.container_type,
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
        """Convert import quotation directly to jobsheet (HBL) without booking"""
        self.ensure_one()
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        all_variants = self.env["sale.order"].search(domain)
        
        hbl = self.env["freight.sea.hbl"].create(
            {
                "sale_order_ids": [(6, 0, all_variants.ids)],
                "root_quotation_id": original_id,
                "freight_type": self.freight_type,
                "container_type": self.container_type,
                "customer_id": self.partner_id.id,
                "term_payment": self.payment_term_id.id,
                "job_date": fields.Date.today(),
                "company_id": self.company_id.id,
            }
        )
        all_variants.write({"sea_hbl_id": hbl.id})
        # FF-73 UAT fix (Masalah 2): mirror eksplisit ke field lokal
        # hbl_ids (compatibility mirror, bukan pengganti sea_hbl_id) --
        # parity dengan booking_ids di atas / air_booking_ids milik Air.
        all_variants.write({"hbl_ids": [(4, hbl.id)]})
        return {
            "type": "ir.actions.act_window",
            "name": "Sea Jobsheet",
            "res_model": "freight.sea.hbl",
            "res_id": hbl.id,
            "view_mode": "form",
            "target": "current",
        }
