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

    hbl_no = fields.Char(string="B/L No.", required=True, default=lambda self: "New", copy=False, readonly=True)
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=False,
    )

    # Direct relasi ke quotation (untuk import flow tanpa booking)
    quotation_id = fields.Many2one(
        "freight.sea.quotation",
        string="Quotation",
        required=False,
        ondelete="set null",
    )

    # Counter fields untuk smart buttons
    quotation_count = fields.Integer(
        string="Quotation Count", compute="_compute_quotation_count"
    )
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_booking_count"
    )

    @api.depends("quotation_id")
    def _compute_quotation_count(self):
        for rec in self:
            rec.quotation_count = 1 if rec.quotation_id else 0

    @api.depends("booking_id")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = 1 if rec.booking_id else 0

    def action_view_quotation(self):
        self.ensure_one()
        if not self.quotation_id:
            return False

        return {
            "name": "Sea Quotation",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.quotation",
            "res_id": self.quotation_id.id,
            "view_mode": "form",
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
    container_type = fields.Selection(
        selection=[("fcl", "FCL"), ("lcl", "LCL"), ("consol", "Consol")],
        string="Container Type",
        required=True,
    )
    job_no = fields.Char(string="Job No.", default=lambda self: "New", copy=False, readonly=True)
    job_date = fields.Date(string="Job Date")
    job_city_id = fields.Many2one("res.city", string="Job City")
    master_job_no = fields.Char(string="Master Job No.")
    original_bl_no = fields.Char(string="Original BL No.")
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
    purchase_order_ids = fields.One2many(
        "freight.sea.hbl.purchase.order",
        "hbl_id",
        string="Purchase Order",
    )
    sales_order_ids = fields.One2many(
        "freight.sea.hbl.sales.order",
        "hbl_id",
        string="Sales Order",
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
        return super().create(vals_list)