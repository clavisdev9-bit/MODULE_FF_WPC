from odoo import api, fields, models
from odoo.exceptions import UserError


class SeaQuotation(models.Model):
    _inherit = "sale.order"

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
    sea_hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Sea Jobsheet",
        index=True,
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

    @api.constrains("is_freight_quotation", "freight_business_type", "container_type")
    def _check_sea_container_type_required(self):
        for rec in self:
            if (
                rec.is_freight_quotation
                and rec.freight_business_type == "sea"
                and not rec.container_type
            ):
                raise UserError("Container Type is required for a Sea Freight Quotation.")

    @api.depends("booking_ids")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)

    @api.depends("sea_hbl_id")
    def _compute_hbl_count(self):
        for rec in self:
            count = 0
            if hasattr(rec, "sea_hbl_id") and rec.sea_hbl_id:
                count = 1
            else:
                count = self.env["freight.sea.hbl"].search_count([("sale_order_ids", "=", rec.id)])
            rec.hbl_count = count

    # =========================================================
    # Sea-specific Actions
    # =========================================================

    def action_view_bookings(self):
        self.ensure_one()
        bookings = self.booking_ids
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
        hbls = self.sea_hbl_id or self.env["freight.sea.hbl"].search([("sale_order_ids", "=", self.id)])
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
