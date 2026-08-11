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
    _rec_name = "hbl_no"

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

    hbl_no = fields.Char(string="B/L No.", required=True, default=lambda self: "New", copy=False, readonly=True)
    master_bl_no = fields.Char(string="OB/L No.", related="booking_id.bl_no", store=True, readonly=False)
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=False,
    )

    # Direct relasi ke quotation (untuk import flow tanpa booking)
    sale_order_ids = fields.Many2many(
        "sale.order",
        string="Sales Orders",
    )
    
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
    )

    # Counter fields untuk smart buttons
    sales_order_count = fields.Integer(
        string="Sales Order Count", compute="_compute_sales_order_count"
    )
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_booking_count"
    )

    @api.depends("sale_order_ids")
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)

    @api.onchange("to_city")
    def _onchange_to_city(self):
        for rec in self:
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

    @api.depends("booking_id")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = 1 if rec.booking_id else 0

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

    # Header Information
    freight_type = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Type",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    container_type = fields.Selection(
        selection=[("fcl", "FCL"), ("lcl", "LCL"), ("consol", "Consol")],
        string="Container Type",
        required=True,
    )
    job_no = fields.Char(string="Job No.", default=lambda self: "New", copy=False)
    job_date = fields.Date(string="Job Date")
    job_city_id = fields.Many2one("res.city", string="Job City")
    master_job_no = fields.Char(string="Master Job No.")
    original_bl_no = fields.Char(string="No. of Original B/L")
    shipment_type = fields.Selection(
        selection=[("sea", "Sea"), ("air", "Air"), ("multimodal", "Multimodal")],
        string="Shipment Type",
    )
    bl_surrendered = fields.Boolean(string="BL Surrendered")

    # NOTE: field khusus HBL, tidak ada di mixin (Booking tidak butuh field ini).
    # Dulu didefinisikan di model perantara freight.sea.hbl.shipment.info,
    # sekarang dipindahkan langsung ke sini karena model perantara dihapus.
    # Saling eksklusif dengan stuffing_location_id (dari mixin) berdasarkan
    # freight_type -- lihat kondisi invisible di views/sea/hbl/hbl.xml.
    warehouse_location_id = fields.Many2one(
        "stock.warehouse",
        string="Warehouse Location",
    )

    # NOTE (FF-21): field baru untuk report "Shipping Instruction".
    # Diisi manual oleh staff, BUKAN hasil konversi angka-ke-kata otomatis --
    # sesuai contoh lampiran PDF, isinya berupa catatan bebas (mis. "PLS
    # ISSUED SEAWAYBILL"), bukan selalu representasi jumlah paket.
    total_packages_remark = fields.Char(
        string="Total No. of Packages/Units (in words)"
    )

    # Customer & Sales
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        domain="[('category_id.name', '=', 'Customer')]",
    )
    customer_ref = fields.Char(
        related="customer_id.ref",
        string="Customer Reference"
    )
    term_payment = fields.Many2one(
        "account.payment.term", 
        string="Terms of Payment"
    )
    salesman_id = fields.Many2one(
        "hr.employee",
        string="Salesman"
    )
    export_sales_team_id = fields.Many2one(
        "res.partner",
        string="Export Sales Team",
        domain="[('category_id.name', '=', 'Sales Team')]"
    )

    # Notify Party
    # NOTE: field notify_id dan notify_address digantikan oleh notify_party_id
    # dan notify_party_address dari freight.sea.bl.info.mixin (FF-29).

    # Delivery & Freight
    # NOTE: delivery_agent_id dan delivery_agent_address dipindahkan ke
    # freight.sea.bl.info.mixin (FF-29).
    freight = fields.Selection(
        selection=[
            ("prepaid", "Prepaid"),
            ("collect", "Collect"),
        ],
        string="Freight",
    )

    pbm = fields.Char(string="PBM")
    custom_permit_ids = fields.One2many(
        "freight.sea.hbl.custom.permit",
        "hbl_id",
        string="Custom Permit",
    )
    cargo_info_ids = fields.One2many(
        "freight.sea.hbl.cargo.info",
        "hbl_id",
        string="Cargo Info",
    )
    purchase_order_ids = fields.Many2many(
        "purchase.order",
        string="Purchase Orders",
    )

    tax_refund_doc_ids = fields.One2many(
        "freight.sea.hbl.tax.refund.doc",
        "hbl_id",
        string="Tax Refund Doc",
    )
    invoice_ids = fields.One2many(
        "freight.sea.hbl.invoice",
        "hbl_id",
        string="Invoice",
    )
    debit_note_ids = fields.One2many(
        "freight.sea.hbl.debit.note",
        "hbl_id",
        string="Debit Note",
    )
    credit_note_ids = fields.One2many(
        "freight.sea.hbl.credit.note",
        "hbl_id",
        string="Credit Note",
    )
    provision_cost_ids = fields.One2many(
        "freight.sea.hbl.provision.cost",
        "hbl_id",
        string="Provision Cost",
    )
    vendor_invoice_ids = fields.One2many(
        "freight.sea.hbl.vendor.invoice",
        "hbl_id",
        string="Vendor Invoice",
    )
    vendor_debit_note_ids = fields.One2many(
        "freight.sea.hbl.vendor.debit.note",
        "hbl_id",
        string="Vendor Debit Note",
    )
    vendor_credit_note_ids = fields.One2many(
        "freight.sea.hbl.vendor.credit.note",
        "hbl_id",
        string="Vendor Credit Note",
    )
    cash_purchase_ids = fields.One2many(
        "freight.sea.hbl.cash.purchase",
        "hbl_id",
        string="Cash Purchase",
    )

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
            
            # Sync to Sales Order Lines
            if rec.sale_order_ids:
                for so in rec.sale_order_ids:
                    # Update header if field exists
                    if hasattr(so, 'analytic_account_id') and not so.analytic_account_id:
                        so.analytic_account_id = rec.analytic_account_id.id
                    # Update all order lines
                    for line in so.order_line:
                        if not line.analytic_distribution:
                            # Bypass locked order check by writing directly to DB
                            self.env.cr.execute(
                                "UPDATE sale_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(['analytic_distribution'])
                            
            # Sync to Purchase Order Lines
            if rec.purchase_order_ids:
                for po in rec.purchase_order_ids:
                    for line in po.order_line:
                        if not line.analytic_distribution:
                            self.env.cr.execute(
                                "UPDATE purchase_order_line SET analytic_distribution = %s WHERE id = %s",
                                (json.dumps(distribution), line.id)
                            )
                            line.invalidate_recordset(['analytic_distribution'])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sequence_date = fields.Date.to_date(
                vals.get("job_date") or fields.Date.context_today(self)
            )
            container_type = vals.get("container_type", "fcl")
            if container_type == "lcl":
                bl_seq_code = "freight.sea.hbl.bl_no.lcl"
            elif container_type == "consol":
                bl_seq_code = "freight.sea.hbl.bl_no.consol"
            else:
                bl_seq_code = "freight.sea.hbl.bl_no"
                
            if not vals.get("hbl_no") or vals.get("hbl_no") == "New":
                vals["hbl_no"] = self.env["ir.sequence"].next_by_code(
                    bl_seq_code, sequence_date=sequence_date
                ) or "New"
            if not vals.get("job_no") or vals.get("job_no") == "New":
                vals["job_no"] = self.env["ir.sequence"].next_by_code(
                    "freight.sea.hbl.job_no", sequence_date=sequence_date
                ) or "New"
                
        records = super().create(vals_list)
        
        # Auto-create analytic account for each jobsheet
        plan = self.env["account.analytic.plan"].search([], limit=1)
        for rec in records:
            if not rec.analytic_account_id:
                analytic_acc = self.env["account.analytic.account"].create({
                    "name": rec.hbl_no,
                    "plan_id": plan.id if plan else False,
                    "partner_id": rec.customer_id.id,
                    "company_id": rec.company_id.id,
                })
                rec.analytic_account_id = analytic_acc.id
                
        records._sync_analytic_to_related_docs()
        return records