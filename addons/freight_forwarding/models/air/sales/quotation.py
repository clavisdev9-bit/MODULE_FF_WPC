from odoo import api, fields, models
from odoo.exceptions import UserError


class AirQuotation(models.Model):
    _inherit = "sale.order"

    # =========================================================
    # Air-specific Fields (dulu di model terpisah freight.air.quotation,
    # digabung langsung ke sale.order — lihat pola yang sama di Sea)
    # =========================================================

    transportation_method = fields.Selection(
        selection=[
            ("air", "Air"),
            ("ocean", "Ocean"),
            ("domestic", "Domestic Ground Transportation"),
        ],
        string="Transportation Method",
    )
    expiry_date = fields.Date(string="Expiry Date")
    source_street = fields.Char(string="Source Street")
    source_street2 = fields.Char(string="Source Street 2")
    source_city = fields.Char(string="Source City")
    source_state_id = fields.Many2one("res.country.state", string="Source State")
    source_zip = fields.Char(string="Source Zip")
    source_country_id = fields.Many2one("res.country", string="Source Country")

    destination_street = fields.Char(string="Destination Street")
    destination_street2 = fields.Char(string="Destination Street 2")
    destination_city = fields.Char(string="Destination City")
    destination_state_id = fields.Many2one(
        "res.country.state", string="Destination State"
    )
    destination_zip = fields.Char(string="Destination Zip")
    destination_country_id = fields.Many2one(
        "res.country", string="Destination Country"
    )

    fumigation = fields.Char(string="Fumigation")
    # Nama field berbeda dari shipping_line_id milik Sea (res.partner) karena
    # comodel-nya berbeda (freight.carrier) — dua field beda tipe tidak bisa
    # berbagi nama yang sama di model sale.order yang sekarang digabung.
    air_shipping_line_id = fields.Many2one("freight.carrier", string="Air Shipping Line")

    # Relasi many2many — nama tabel relasi air-specific
    transaction_ids = fields.Many2many(
        "payment.transaction",
        "freight_air_quotation_transaction_rel",
        "air_quotation_id",
        "transaction_id",
        string="Transactions",
        copy=False,
    )
    tag_ids = fields.Many2many(
        "crm.tag",
        "freight_air_quotation_tag_rel",
        "air_quotation_id",
        "tag_id",
        string="Tags",
    )

    # FF-73 follow-up (generic Duplicate fix): copy=False -- lihat komentar
    # setara di SeaQuotation.booking_ids/sea_job_ids/sea_job_id. Tanpa ini,
    # generic copy() menyalin air_booking_ids/air_job_id milik record
    # SUMBER ke record BARU yang independen, lalu AirQuotation.create() di
    # bawah menuliskannya balik ke Booking/HAWB.sale_order_ids -- constraint
    # commercial-group mixin menolak karena duplicate itu bukan anggota
    # commercial group manapun. Currency variant tetap tersinkron lewat
    # "all_variants.write(...)" eksplisit di action convert (tidak bergantung
    # pada copy() field inheritance untuk ini).
    air_booking_ids = fields.Many2many(
        "freight.air.booking",
        string="Air Bookings",
        copy=False,
    )
    air_job_id = fields.Many2one(
        "freight.air.job",
        string="Air Jobsheet (HAWB)",
        index=True,
        copy=False,
    )
    air_booking_count = fields.Integer(
        string="Air Booking Count", compute="_compute_air_booking_count"
    )
    air_job_count = fields.Integer(
        string="Air Jobsheet Count", compute="_compute_air_job_count"
    )

    @api.depends("air_booking_ids")
    def _compute_air_booking_count(self):
        for rec in self:
            rec.air_booking_count = len(rec.air_booking_ids)

    @api.depends("air_job_id", "original_quotation_id")
    def _compute_air_job_count(self):
        """FF-73: resolve lewat commercial group -- lihat SeaQuotation._compute_hbl_count."""
        for rec in self:
            rec.air_job_count = len(rec._get_commercial_group_jobsheets("freight.air.job"))

    def action_view_air_bookings(self):
        self.ensure_one()
        bookings = self.air_booking_ids
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({"default_sale_order_ids": [self.id]})
        return {
            "name": "Air Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.air.booking",
            "view_mode": "form" if len(bookings) == 1 else "list,form",
            "domain": [("id", "in", bookings.ids)],
            "res_id": bookings.id if len(bookings) == 1 else False,
            "context": ctx,
        }

    def action_view_air_jobs(self):
        self.ensure_one()
        hawbs = self._get_commercial_group_jobsheets("freight.air.job")
        ctx = {k: v for k, v in self.env.context.items() if not k.endswith("_view_ref")}
        ctx.update({"default_sale_order_ids": [self.id]})
        return {
            "name": "Air Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.air.job",
            "view_mode": "form" if len(hawbs) == 1 else "list,form",
            "domain": [("id", "in", hawbs.ids)],
            "res_id": hawbs.id if len(hawbs) == 1 else False,
            "context": ctx,
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if hasattr(rec, "air_job_id") and rec.air_job_id:
                if hasattr(rec.air_job_id, "sale_order_ids") and rec.id not in rec.air_job_id.sale_order_ids.ids:
                    rec.air_job_id.sale_order_ids = [(4, rec.id)]
            if hasattr(rec, "air_booking_ids") and rec.air_booking_ids:
                for bkg in rec.air_booking_ids:
                    if hasattr(bkg, "sale_order_ids") and rec.id not in bkg.sale_order_ids.ids:
                        bkg.sale_order_ids = [(4, rec.id)]
        return records

    def write(self, vals):
        res = super().write(vals)
        if "air_job_id" in vals:
            for rec in self:
                if hasattr(rec, "air_job_id") and rec.air_job_id and hasattr(rec.air_job_id, "sale_order_ids"):
                    if rec.id not in rec.air_job_id.sale_order_ids.ids:
                        rec.air_job_id.sale_order_ids = [(4, rec.id)]
        if "air_booking_ids" in vals:
            for rec in self:
                for bkg in rec.air_booking_ids:
                    if hasattr(bkg, "sale_order_ids") and rec.id not in bkg.sale_order_ids.ids:
                        bkg.sale_order_ids = [(4, rec.id)]
        return res

    def _action_convert_to_booking_direct_air(self):
        self.ensure_one()
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        all_variants = self.env["sale.order"].search(domain)
        
        booking_vals = {
            "partner_id": self.partner_id.id,
            "customer_reference": self.reference_number or self.client_order_ref or False,
            "salesman_id": (
                self.user_id.id or
                (self.salesman_id.user_id.id if hasattr(self.salesman_id, "user_id") and self.salesman_id.user_id else self.env.uid)
            ),
            "payment_term_id": self.payment_term_id.id if self.payment_term_id else False,
            "freight_type": self.freight_type,
            "company_id": self.company_id.id,
            "commodity_id": self.commodity_id.id if self.commodity_id else False,
            "delivery_type": self.delivery_type_id.id if self.delivery_type_id else False,
            "sale_order_ids": [(6, 0, all_variants.ids)],
            "source_quotation_id": original_id,
        }

        booking = self.env["freight.air.booking"].create(booking_vals)
        all_variants.write({"air_booking_ids": [(4, booking.id)]})

        return {
            "type": "ir.actions.act_window",
            "name": "Air Booking",
            "res_model": "freight.air.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "target": "current",
        }

    def _action_convert_to_jobsheet_direct_air(self):
        """FF-75: Import quotation -> Create Job TANPA Booking. Membuat 1
        Master Job + 1 House Job pertama yang diprefill dari Quotation aktif,
        langsung ter-gabung (master_job_id) ke Master tersebut.

        Master DI SINI BUKAN container kosong -- lihat komentar lengkap di
        _action_convert_to_jobsheet_direct_sea (Sea). Master tetap
        freight.air.job penuh, hanya belum ada Booking untuk menyalin data
        awal."""
        self.ensure_one()

        master = self.env["freight.air.job"].create({
            "shipment_type": "master",
            "freight_type": self.freight_type,
            "company_id": self.company_id.id,
        })
        house_vals = self.env["freight.air.job"]._prepare_house_vals_from_quotation(
            self, master=master
        )
        house = self.env["freight.air.job"].create(house_vals)
        all_variants = house.source_quotation_id | house.source_quotation_id.variant_ids
        all_variants.write({"air_job_id": house.id})

        return {
            "type": "ir.actions.act_window",
            "name": "Air Job",
            "res_model": "freight.air.job",
            # Master dibuka (bukan House) -- konsisten dengan flow Export,
            # lihat komentar setara di _action_convert_to_jobsheet_direct_sea.
            "res_id": master.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_air_add_to_master_wizard(self):
        """FF-75 follow-up (method collision fix): nama method di-prefix
        `air_` -- lihat komentar setara di
        SeaQuotation.action_open_sea_add_to_master_wizard. 'Add to Master'
        -- Freight Actions Export. Membuat House Job baru dari Quotation
        aktif dan menggabungkannya ke Master Air existing (dipilih lewat
        wizard), TANPA membuat Booking baru."""
        self.ensure_one()
        if self.freight_type != "export":
            raise UserError("Add to Master hanya berlaku untuk Quotation Export.")
        return {
            "type": "ir.actions.act_window",
            "name": "Add to Master",
            "res_model": "freight.air.add.to.master.wizard",
            "view_mode": "form",
            "target": "new",
            "context": dict(self.env.context, default_quotation_id=self.id),
        }
