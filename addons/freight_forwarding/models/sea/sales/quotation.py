from odoo import api, fields, models
from odoo.exceptions import UserError


class SeaQuotation(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "freight.quotation"]
    _description = "Sea Quotation"

    # =========================================================
    # Sea-specific Fields
    # =========================================================

    # Relasi booking & HBL
    booking_ids = fields.Many2many(
        "freight.sea.booking",
        string="Sea Bookings"
    )
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_booking_count"
    )
    hbl_count = fields.Integer(
        string="Jobsheet Count", compute="_compute_hbl_count"
    )

    # Multi-currency variant tracking
    original_quotation_id = fields.Many2one(
        "sale.order",
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

    def _compute_hbl_count(self):
        for rec in self:
            count = 0
            if hasattr(rec, "sea_hbl_id") and rec.sea_hbl_id:
                count = 1
            else:
                count = self.env["freight.sea.hbl"].search_count([("sale_order_ids", "=", rec.id)])
            rec.hbl_count = count

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
        if not self.is_freight_quotation:
            raise UserError("This action is only available for Freight Quotations.")
        if self.original_quotation_id:
            raise UserError("You cannot create a currency variant from a child quotation. Please create it from the parent quotation instead.")

        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        new_variant = self.copy(default={
            'original_quotation_id': original_id,
            'order_line': [],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': new_variant.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # =========================================================
    # Sea-specific Actions
    # =========================================================

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

    def action_view_currency_variants(self):
        self.ensure_one()
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        
        return {
            "name": "Currency Variants",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
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
            "context": dict(self.env.context, default_sale_order_ids=[self.id]),
        }

    def action_view_hbls(self):
        self.ensure_one()
        hbls = self.sea_hbl_id or self.env["freight.sea.hbl"].search([("sale_order_ids", "=", self.id)])
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context, default_sale_order_ids=[self.id]),
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

    def _prepare_booking_cargo_info_vals(self, cargo_info, booking):
        return {
            "booking_id": booking.id,
            "package_type_id": cargo_info.package_type_id.id if cargo_info.package_type_id else False,
            "container_no": cargo_info.container_no,
            "seal_no": cargo_info.seal_no,
            "description_of_goods": cargo_info.description_of_goods,
            "marks_and_no": cargo_info.marks_and_no,
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
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        all_variants = self.env["sale.order"].search(domain)
        
        hbl = self.env["freight.sea.hbl"].create(
            {
                "sale_order_ids": [(6, 0, all_variants.ids)],
                "freight_type": self.freight_type,
                "container_type": self.container_type,
                "customer_id": self.partner_id.id,
                "term_payment": self.payment_term_id.id,
                "job_date": fields.Date.today(),
                "company_id": self.company_id.id,
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
