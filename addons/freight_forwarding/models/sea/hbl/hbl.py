from odoo import api, fields, models


class SeaHBL(models.Model):
    _name = "freight.sea.hbl"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "freight.sea.shipment.info.mixin",
        "freight.sea.vessel.details.mixin",
        "freight.sea.bl.info.mixin",
    ]
    _description = "Sea Jobsheet"
    _rec_name = "job_no"

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
    hbl_no = fields.Char(string="HBL No.", copy=False)
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
    vessel_voy = fields.Char(string="Vessel / Voyage")
    bl_no = fields.Char(string="B/L No.")
    carrier_id = fields.Many2one(
        "res.partner",
        string="Carrier / Shipping Line",
        related="shipping_line_id",
        store=False,
        readonly=True,
    )
    pol_id = fields.Many2one(
        "freight.port",
        string="Port of Loading",
        related="port_of_loading_id",
        store=False,
        readonly=True,
    )
    pod_id = fields.Many2one(
        "freight.port",
        string="Port of Discharge",
        related="port_of_discharge_id",
        store=False,
        readonly=True,
    )
    do_ready_date = fields.Date(string="DO Ready On")
    port_code = fields.Char(string="Port Code")
    container_seal_ids = fields.Char(string="Container / Seal No.", compute="_compute_container_seal_ids", store=False)
    cargo_line_ids = fields.One2many(
        "freight.sea.hbl.cargo.info",
        "hbl_id",
        string="Cargo Lines",
        related="cargo_info_ids",
        readonly=True,
    )
    remarks = fields.Text(string="Remarks")

    sales_order_count = fields.Integer(string="Sales Order Count", compute="_compute_sales_order_count")
    booking_count = fields.Integer(string="Booking Count", compute="_compute_booking_count")

    freight_type = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Type",
        required=True,
    )
    container_type = fields.Selection(
        selection=[("fcl", "FCL"), ("lcl", "LCL"), ("consol", "Consol")],
        string="Container Type",
        required=True,
    )
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
    master_job_no = fields.Char(string="Master Job No.")
    no_of_original_bl = fields.Char(string="No. of Original B/L")
    mbl_no = fields.Char(string="MBL No.")
    shipment_type = fields.Selection(
        selection=[("sea", "Sea"), ("air", "Air"), ("multimodal", "Multimodal")],
        string="Shipment Type",
    )
    bl_surrendered = fields.Boolean(string="BL Surrendered")
    delivery_type_id = fields.Many2one("freight.delivery.type", string="Delivery Type")
    do_ready_on = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Do Ready On")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        domain="[('category_id.name', '=', 'Customer')]",
    )
    customer_ref = fields.Char(string="Customer Reference")
    actual_shipper = fields.Boolean(string="Actual Shipper")
    term_payment = fields.Many2one("account.payment.term", string="Terms of Payment")
    salesman_id = fields.Many2one("hr.employee", string="Salesman")
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
    
    warehouse_location_id = fields.Many2one("stock.warehouse", string="Warehouse Location")
    total_packages_remark = fields.Char(string="Total No. of Packages/Units (in words)")
    pbm = fields.Char(string="PBM")

    sale_order_ids = fields.Many2many("sale.order", string="Sales Orders")
    purchase_order_ids = fields.Many2many("purchase.order", string="Purchase Orders")
    custom_permit_ids = fields.One2many("freight.sea.hbl.custom.permit", "hbl_id", string="Custom Permit")
    cargo_info_ids = fields.One2many("freight.sea.hbl.cargo.info", "hbl_id", string="Cargo Info")
    tax_refund_doc_ids = fields.One2many("freight.sea.hbl.tax.refund.doc", "hbl_id", string="Tax Refund Doc")
    invoice_ids = fields.One2many("freight.sea.hbl.invoice", "hbl_id", string="Invoice")
    debit_note_ids = fields.One2many("freight.sea.hbl.debit.note", "hbl_id", string="Debit Note")
    credit_note_ids = fields.One2many("freight.sea.hbl.credit.note", "hbl_id", string="Credit Note")
    provision_cost_ids = fields.One2many("freight.sea.hbl.provision.cost", "hbl_id", string="Provision Cost")
    vendor_invoice_ids = fields.One2many("freight.sea.hbl.vendor.invoice", "hbl_id", string="Vendor Invoice")
    vendor_debit_note_ids = fields.One2many("freight.sea.hbl.vendor.debit.note", "hbl_id", string="Vendor Debit Note")
    vendor_credit_note_ids = fields.One2many("freight.sea.hbl.vendor.credit.note", "hbl_id", string="Vendor Credit Note")
    cash_purchase_ids = fields.One2many("freight.sea.hbl.cash.purchase", "hbl_id", string="Cash Purchase")

    yard_id = fields.Many2one(
        "stock.warehouse",
        string="Yard",
        domain=[],
    )
    yard_code = fields.Char(
        string="Yard Code",
        related=None,
        compute=False,
        readonly=False,
        store=True,
    )
    yard_address = fields.Char(
        string="Yard Address",
        related=None,
        compute=False,
        readonly=False,
        store=True,
    )

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

    @api.onchange("yard_id")
    def _onchange_yard_id(self):
        for rec in self:
            rec.yard_code = rec.yard_id.code or False
            rec.yard_address = (
                rec.yard_id.partner_id._display_address()
                if rec.yard_id.partner_id
                else False
            )

    @api.depends("sale_order_ids")
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    @api.depends("booking_id")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = 1 if rec.booking_id else 0

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

        return {
            "name": "Sales Orders",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form" if len(orders) == 1 else "list,form",
            "domain": [("id", "in", orders.ids)],
            "res_id": orders.id if len(orders) == 1 else False,
            "context": dict(self.env.context),
        }

    def action_view_booking(self):
        self.ensure_one()
        if not self.booking_id:
            return False

        return {
            "name": "Sea Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "res_id": self.booking_id.id,
            "view_mode": "form",
            "context": dict(self.env.context),
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sequence_date = fields.Date.to_date(
                vals.get("job_date") or fields.Date.context_today(self)
            )
            if not vals.get("job_no") or vals.get("job_no") == "New":
                vals["job_no"] = self.env["ir.sequence"].next_by_code(
                    "freight.sea.hbl.job_no", sequence_date=sequence_date
                ) or "New"
                
        records = super().create(vals_list)
        
        plan = self.env["account.analytic.plan"].search([], limit=1)
        for rec in records:
            if not rec.analytic_account_id:
                analytic_acc = self.env["account.analytic.account"].create({
                    "name": rec.job_no,
                    "plan_id": plan.id if plan else False,
                    "partner_id": rec.customer_id.id,
                    "company_id": rec.company_id.id,
                })
                rec.analytic_account_id = analytic_acc.id
                
        records._sync_analytic_to_related_docs()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_analytic_to_related_docs()
        return res

    def _sync_analytic_to_related_docs(self):
        import json
        for rec in self:
            if not rec.analytic_account_id:
                continue
            
            distribution = {str(rec.analytic_account_id.id): 100.0}
            
            if rec.sale_order_ids:
                for so in rec.sale_order_ids:
                    if hasattr(so, 'analytic_account_id') and not so.analytic_account_id:
                        so.analytic_account_id = rec.analytic_account_id.id
                    for line in so.order_line:
                        if not line.analytic_distribution:
                            self.env.cr.execute(
                                "UPDATE sale_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(['analytic_distribution'])
                            
            if rec.purchase_order_ids:
                for po in rec.purchase_order_ids:
                    for line in po.order_line:
                        if not line.analytic_distribution:
                            self.env.cr.execute(
                                "UPDATE purchase_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(['analytic_distribution'])