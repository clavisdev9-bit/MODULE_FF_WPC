from odoo import api, fields, models


class AirQuotation(models.Model):
    _name = "freight.air.quotation"
    _inherit = ["sale.order", "freight.quotation"]
    _description = "Air Quotation"
    _rec_name = "name"

    # Nama tabel DB untuk _sync_sale_order_rows() di mixin
    _quotation_table = "freight_air_quotation"

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
        "valid_from",
        "container_type",
        "terms_and_conditions",
    )

    # =========================================================
    # Air-specific Fields
    # =========================================================

    # Container Type (sama seperti sea, di-sync ke sale_order)
    container_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Container Type",
        required=True,
    )

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
    port_of_loading_id = fields.Many2one("freight.port", string="Port Of Loading")
    port_of_discharge_id = fields.Many2one("freight.port", string="Port Of Discharge")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    via2_id = fields.Many2one("freight.port", string="Via2")
    via3_id = fields.Many2one("freight.port", string="Via3")
    shipping_line_id = fields.Many2one("freight.carrier", string="Shipping Line")

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

    # Cargo Info (air-specific comodel)
    cargo_info_ids = fields.One2many(
        "freight.air.quotation.cargo.info",
        "quotation_id",
        string="Cargo Info",
    )

    # Shipment Info — Air-specific (airport / airline) — TODO: akan ditambahkan nanti


class SaleOrderAirCompat(models.Model):
    _inherit = "sale.order"

    air_booking_ids = fields.Many2many(
        "freight.air.booking",
        string="Air Bookings",
    )
    air_hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Air Jobsheet (HAWB)",
        index=True,
    )
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_air_booking_count"
    )
    hawb_count = fields.Integer(
        string="Jobsheet Count", compute="_compute_air_hawb_count"
    )

    def _compute_air_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.air_booking_ids)

    def _compute_air_hawb_count(self):
        for rec in self:
            rec.hawb_count = 1 if rec.air_hawb_id else 0

    def action_view_air_bookings(self):
        self.ensure_one()
        bookings = self.air_booking_ids
        return {
            "name": "Air Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.air.booking",
            "view_mode": "form" if len(bookings) == 1 else "list,form",
            "domain": [("id", "in", bookings.ids)],
            "res_id": bookings.id if len(bookings) == 1 else False,
            "context": dict(self.env.context),
        }

    def action_view_hawbs(self):
        self.ensure_one()
        hawb = self.air_hawb_id
        return {
            "name": "Air Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.air.hawb",
            "view_mode": "form",
            "res_id": hawb.id if hawb else False,
            "context": dict(self.env.context),
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if hasattr(rec, "air_hawb_id") and rec.air_hawb_id:
                if hasattr(rec.air_hawb_id, "sale_order_ids") and rec.id not in rec.air_hawb_id.sale_order_ids.ids:
                    rec.air_hawb_id.sale_order_ids = [(4, rec.id)]
        return records

    def write(self, vals):
        res = super().write(vals)
        if "air_hawb_id" in vals:
            for rec in self:
                if hasattr(rec, "air_hawb_id") and rec.air_hawb_id and hasattr(rec.air_hawb_id, "sale_order_ids"):
                    if rec.id not in rec.air_hawb_id.sale_order_ids.ids:
                        rec.air_hawb_id.sale_order_ids = [(4, rec.id)]
        return res

    def _prepare_booking_cargo_info_vals(self, cargo_info, booking):
        return {
            "booking_id": booking.id,
            "package_type_id": cargo_info.package_type_id.id if getattr(cargo_info, "package_type_id", False) else False,
            "description_of_goods": getattr(cargo_info, "description_of_goods", False),
            "marks_and_no": getattr(cargo_info, "marks_and_no", False),
            "types_of_cargo": cargo_info.types_of_cargo.id if getattr(cargo_info, "types_of_cargo", False) else False,
            "quantity": getattr(cargo_info, "quantity", 0),
            "length": getattr(cargo_info, "length", 0.0),
            "width": getattr(cargo_info, "width", 0.0),
            "height": getattr(cargo_info, "height", 0.0),
            "gross_weight": getattr(cargo_info, "gross_weight", 0.0),
            "net_weight": getattr(cargo_info, "net_weight", 0.0),
            "volume": getattr(cargo_info, "volume", 0.0),
            "total_volume": getattr(cargo_info, "total_volume", 0.0),
            "harmonize": getattr(cargo_info, "harmonize", False),
            "temperature": getattr(cargo_info, "temperature", False),
            "ventilation": getattr(cargo_info, "ventilation", False),
            "humidity": getattr(cargo_info, "humidity", False),
            "has_dangerous_goods": getattr(cargo_info, "has_dangerous_goods", False),
            "imdg_code": getattr(cargo_info, "imdg_code", False),
            "class_number": getattr(cargo_info, "class_number", False),
            "packing_group": getattr(cargo_info, "packing_group", False),
            "a_number": getattr(cargo_info, "a_number", False),
            "flash_point": getattr(cargo_info, "flash_point", False),
            "material_description": getattr(cargo_info, "material_description", False),
        }

    def _copy_cargo_info_to_booking(self, booking):
        if "freight.air.booking.cargo.info" in self.env and hasattr(self, "cargo_info_ids"):
            booking_detail_model = self.env["freight.air.booking.cargo.info"]
            for cargo_info in self.cargo_info_ids:
                booking_detail_model.create(
                    self._prepare_booking_cargo_info_vals(cargo_info, booking)
                )

    def action_convert_to_booking_direct(self):
        self.ensure_one()
        if self.freight_business_type != "air" and hasattr(super(), "action_convert_to_booking_direct"):
            return super().action_convert_to_booking_direct()
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
            "quotation_id": self.id,
        }
        
        if "sale_order_ids" in self.env["freight.air.booking"]._fields:
            booking_vals["sale_order_ids"] = [(6, 0, all_variants.ids)]

        booking = self.env["freight.air.booking"].create(booking_vals)
        all_variants.write({"air_booking_ids": [(4, booking.id)]})
        self._copy_cargo_info_to_booking(booking)
        
        return {
            "type": "ir.actions.act_window",
            "name": "Air Booking",
            "res_model": "freight.air.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_convert_to_jobsheet_direct(self):
        """Convert quotation directly to jobsheet (HAWB) without booking"""
        self.ensure_one()
        if self.freight_business_type != "air" and hasattr(super(), "action_convert_to_jobsheet_direct"):
            return super().action_convert_to_jobsheet_direct()
        original_id = self.original_quotation_id.id if self.original_quotation_id else self.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        all_variants = self.env["sale.order"].search(domain)

        hawb_vals = {
            "freight_type": self.freight_type,
            "partner_id": self.partner_id.id,
            "customer_ref": self.reference_number or self.client_order_ref or False,
            "term_payment": self.payment_term_id.id if self.payment_term_id else False,
            "salesman_id": (
                self.user_id.id or 
                (self.salesman_id.user_id.id if hasattr(self.salesman_id, "user_id") and self.salesman_id.user_id else self.env.uid)
            ),
            "company_id": self.company_id.id,
        }

        if "sale_order_ids" in self.env["freight.air.hawb"]._fields:
            hawb_vals["sale_order_ids"] = [(6, 0, all_variants.ids)]

        hawb = self.env["freight.air.hawb"].create(hawb_vals)
        all_variants.write({"air_hawb_id": hawb.id})
        
        return {
            "type": "ir.actions.act_window",
            "name": "Air Jobsheet",
            "res_model": "freight.air.hawb",
            "res_id": hawb.id,
            "view_mode": "form",
            "target": "current",
        }
