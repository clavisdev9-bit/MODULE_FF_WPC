from odoo import api, fields, models
from odoo.exceptions import UserError


class SeaQuotation(models.Model):
    _name = "freight.sea.quotation"
    _inherit = ["sale.order", "freight.quotation"]
    _description = "Sea Quotation"
    _rec_name = "name"

    # Nama tabel DB untuk _sync_sale_order_rows() di mixin
    _quotation_table = "freight_sea_quotation"

    _SALE_ORDER_SYNC_COLUMNS = (
        "campaign_id",
        "source_id",
        "medium_id",
        "company_id",
        "partner_id",
        "partner_invoice_id",
        "partner_shipping_id",
        "fiscal_position_id",
        "payment_term_id",
        "pricelist_id",
        "currency_id",
        "user_id",
        "team_id",
        "create_uid",
        "write_uid",
        "name",
        "state",
        "client_order_ref",
        "origin",
        "reference",
        "invoice_status",
        "validity_date",
        "note",
        "currency_rate",
        "amount_untaxed",
        "amount_tax",
        "amount_total",
        "locked",
        "require_signature",
        "require_payment",
        "create_date",
        "date_order",
        "write_date",
        "picking_policy",
        "effective_date",
        "container_type",
    )

    # =========================================================
    # Sea-specific Fields
    # =========================================================

    # Relasi booking & HBL
    booking_ids = fields.One2many(
        "freight.sea.booking", "quotation_id", string="Sea Bookings"
    )
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_booking_count"
    )
    hbl_count = fields.Integer(
        string="Jobsheet Count", compute="_compute_hbl_count"
    )

    # Multi-currency variant tracking
    original_quotation_id = fields.Many2one(
        "freight.sea.quotation",
        string="Original Quotation",
        copy=False,
        index=True,
    )
    variant_count = fields.Integer(
        string="Variant Count",
        compute="_compute_variant_count"
    )

    # Container Type (sea-specific, juga di-sync ke sale_order)
    container_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Container Type",
        required=True,
    )

    # Relasi many2many — nama tabel relasi sea-specific
    transaction_ids = fields.Many2many(
        "payment.transaction",
        "freight_sea_quotation_transaction_rel",
        "sea_quotation_id",
        "transaction_id",
        string="Transactions",
        copy=False,
    )
    tag_ids = fields.Many2many(
        "crm.tag",
        "freight_sea_quotation_tag_rel",
        "sea_quotation_id",
        "tag_id",
        string="Tags",
    )

    # Cargo Info (comodel sea-specific)
    cargo_info_ids = fields.One2many(
        "freight.sea.quotation.cargo.info",
        "quotation_id",
        string="Cargo Info",
    )

    # Shipment Info — Sea-specific (port / shipping line)
    port_of_loading_id = fields.Many2one("freight.port", string="Port Of Loading")
    port_of_discharge_id = fields.Many2one("freight.port", string="Port Of Discharge")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    shipping_line_id = fields.Many2one(
        "res.partner",
        string="Shipping Line",
        domain="[('category_id.name', '=', 'Shipping Line')]",
    )
    via2_id = fields.Many2one("freight.port", string="Via2")
    via3_id = fields.Many2one("freight.port", string="Via3")

    # =========================================================
    # Sea-specific Compute Methods
    # =========================================================

    @api.depends("booking_ids")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)

    @api.depends("booking_ids.hbl_ids")
    def _compute_hbl_count(self):
        hbl_model = self.env["freight.sea.hbl"]

        # Batch query 1: HBL via booking — group per booking_id
        all_booking_ids = self.booking_ids.ids
        booking_hbl_data = hbl_model.read_group(
            [("booking_id", "in", all_booking_ids)],
            ["booking_id"],
            ["booking_id"],
        )
        # Map booking_id → hbl count
        booking_hbl_count = {
            d["booking_id"][0]: d["booking_id_count"]
            for d in booking_hbl_data
        }

        # Batch query 2: HBL langsung dari quotation (import flow tanpa booking)
        direct_hbl_data = hbl_model.read_group(
            [("quotation_id", "in", self.ids)],
            ["quotation_id"],
            ["quotation_id"],
        )
        direct_hbl_count = {
            d["quotation_id"][0]: d["quotation_id_count"]
            for d in direct_hbl_data
        }

        for rec in self:
            via_booking = sum(
                booking_hbl_count.get(b.id, 0) for b in rec.booking_ids
            )
            rec.hbl_count = via_booking + direct_hbl_count.get(rec.id, 0)

    def _compute_variant_count(self):
        for rec in self:
            if not rec.id:
                rec.variant_count = 0
                continue
                
            original_id = rec.original_quotation_id.id if rec.original_quotation_id else rec.id
            domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
            # Kurangi 1 agar tidak menghitung dirinya sendiri (hanya menghitung varian LAIN)
            count = self.search_count(domain) - 1
            rec.variant_count = count if count > 0 else 0

    def action_create_currency_variant(self):
        """
        Buat salinan header-only yang tertaut ke quotation asal sebagai currency variant.
        Berbeda dari Duplicate standar: tidak menyalin order lines,
        dan otomatis tertaut lewat original_quotation_id.
        """
        self.ensure_one()
        if self.original_quotation_id:
            raise UserError("You cannot create a currency variant from a child quotation. Please create it from the parent quotation instead.")

        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        new_variant = self.copy(default={
            'original_quotation_id': original_id,
            'order_line': [],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'freight.sea.quotation',
            'res_id': new_variant.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # =========================================================
    # Sea-specific Actions
    # =========================================================

    def action_view_currency_variants(self):
        self.ensure_one()
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        
        return {
            "name": "Currency Variants",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.quotation",
            "view_mode": "list,form",
            "domain": domain,
            "context": dict(self.env.context, create=False),
        }

    def action_view_bookings(self):
        self.ensure_one()
        bookings = self.booking_ids
        return {
            "name": "Sea Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "view_mode": "form" if len(bookings) == 1 else "list,form",
            "domain": [("id", "in", bookings.ids)],
            "res_id": bookings.id if len(bookings) == 1 else False,
            "context": dict(self.env.context, default_quotation_id=self.id),
        }

    def action_view_hbls(self):
        self.ensure_one()
        hbls = self.env["freight.sea.hbl"].search(
            [
                "|",
                ("booking_id.quotation_id", "=", self.id),
                ("quotation_id", "=", self.id),
            ]
        )
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context),
        }

    def _prepare_booking_cargo_info_vals(self, cargo_info, booking):
        return {
            "booking_id": booking.id,
            "uom": cargo_info.uom,
            "package_type_id": cargo_info.package_type_id.id if cargo_info.package_type_id else False,
            "container_no": cargo_info.container_no,
            "seal_no": cargo_info.seal_no,
            "container_type_id": cargo_info.container_type_id.id if cargo_info.container_type_id else False,
            "types_of_cargo": cargo_info.types_of_cargo.id if cargo_info.types_of_cargo else False,
            "quantity": cargo_info.quantity,
            "length": cargo_info.length,
            "width": cargo_info.width,
            "height": cargo_info.height,
            "gross_weight": cargo_info.gross_weight,
            "net_weight": cargo_info.net_weight,
            "volume": cargo_info.volume,
            "total_volume": cargo_info.total_volume,
            "harmonize": cargo_info.harmonize,
            "temperature": cargo_info.temperature,
            "ventilation": cargo_info.ventilation,
            "humidity": cargo_info.humidity,
            "has_dangerous_goods": cargo_info.has_dangerous_goods,
            "imdg_code": cargo_info.imdg_code,
            "class_number": cargo_info.class_number,
            "packing_group": cargo_info.packing_group,
            "a_number": cargo_info.a_number,
            "flash_point": cargo_info.flash_point,
            "material_description": cargo_info.material_description,
        }

    def _copy_cargo_info_to_booking(self, booking):
        booking_detail_model = self.env["freight.sea.booking.cargo.info"]
        for cargo_info in self.cargo_info_ids:
            booking_detail_model.create(
                self._prepare_booking_cargo_info_vals(cargo_info, booking)
            )

    def action_convert_to_booking_direct(self):
        self.ensure_one()
        destination_country = (
            self.destination_country_id or self.destination_id.country_id
        )
        origin_country = self.source_country_id or self.origin_id.country_id
        booking_no = self.env["ir.sequence"].next_by_code("freight.sea.booking")
        booking_vals = {
            "name": booking_no,
            "quotation_id": self.id,
            "partner_id": self.partner_id.id,
            "delivery_type_id": self.delivery_type_id.id,
            "port_of_loading_id": self.port_of_loading_id.id,
            "port_of_discharge_id": self.port_of_discharge_id.id,
            "destination_country_id": (
                destination_country.id if destination_country else False
            ),
            "origin_country_id": origin_country.id if origin_country else False,
            "phone": self.phone,
            "email": self.email,
            "salesman_id": self.salesman_id.id,
            "payment_term_id": self.payment_term_id.id,
            "container_type": self.container_type,
            "freight_type": self.freight_type,
            "booking_date": fields.Datetime.now(),
            "job_date": fields.Date.today(),
        }
        booking = self.env["freight.sea.booking"].create(booking_vals)
        self._copy_cargo_info_to_booking(booking)
        return {
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_convert_to_jobsheet_direct(self):
        """Convert import quotation directly to jobsheet (HBL) without booking"""
        self.ensure_one()
        hbl = self.env["freight.sea.hbl"].create(
            {
                "quotation_id": self.id,
                "freight_type": self.freight_type,
                "container_type": self.container_type,
                "customer_id": self.partner_id.id,
                "term_payment": self.payment_term_id.id,
                "job_date": fields.Date.today(),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Sea Jobsheet",
            "res_model": "freight.sea.hbl",
            "res_id": hbl.id,
            "view_mode": "form",
            "target": "current",
        }
