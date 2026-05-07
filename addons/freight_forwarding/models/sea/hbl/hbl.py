from odoo import api, fields, models

class SeaHBL(models.Model):
    _name = "freight.sea.hbl"
    _description = "Sea Jobsheet"
    _rec_name = "hbl_no"

    hbl_no = fields.Char(string="B/L No.", required=True)
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        ondelete="cascade",
        required=True,
    )

    # Header Information
    type = fields.Selection(
        selection=[
            ("Import", "Import"),
            ("Export", "Export"),
        ],
        string="Type",
        required=True,
    )
    freight_type = fields.Selection(
        selection=[("fcl", "FCL"), ("lcl", "LCL"), ("consol", "Consol")],
        string="Freight Type",
        required=True,
    )
    job_no = fields.Char(string="Job No.")
    job_date = fields.Date(string="Job Date")
    job_city_id = fields.Many2one("res.country.state", string="Job City")
    master_job_no = fields.Char(string="Master Job No.")
    original_bl_no = fields.Char(string="Original BL No.")
    shipment_type = fields.Selection(
        selection=[("sea", "Sea"), ("air", "Air"), ("multimodal", "Multimodal")],
        string="Shipment Type",
    )
    bl_surrendered = fields.Boolean(string="BL Surrendered")

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
    shipper_id = fields.Many2one(
        "res.partner",
        string="Shipper",
        domain="[('category_id.name', '=', 'Shipper')]",
    )
    shipper_address = fields.Char(
        related="shipper_id.contact_address",
        string="Shipper Address",
    )
    consignee_id = fields.Many2one(
        "res.partner",
        string="Consignee",
        domain="[('category_id.name', '=', 'Consignee')]",
    )
    consignee_address = fields.Char(
        related="consignee_id.contact_address",
        string="Consignee Address",
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
    notify_id = fields.Many2one(
        "res.partner",
        string="Notify",
        domain="[('category_id.name', '=', 'Notify Party')]",
    )
    notify_address = fields.Char(
        related="notify_id.contact_address",
        string="Notify Address",
    )

    # Delivery & Freight
    delivery_agent_id = fields.Many2one(
        "res.partner",
        string="Delivery Agent",
        domain="[('category_id.name', '=', 'Delivery Agent')]",
    )
    delivery_agent_address = fields.Char(
        related="delivery_agent_id.contact_address",
        string="Delivery Agent Address",
    )
    freight = fields.Selection(
        selection=[
            ("prepaid", "Prepaid"),
            ("collect", "Collect"),
        ],
        string="Freight",
    )

    shipment_info_ids = fields.One2many(
        "freight.sea.hbl.shipment.info",
        "hbl_id",
        string="Shipment Info",
    )
    vessel_details_ids = fields.One2many(
        "freight.sea.hbl.vessel.details",
        "hbl_id",
        string="Vessel Details",
    )
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
            month_value = sequence_date.strftime("%m")
            year_value = sequence_date.strftime("%y")
            if not vals.get("hbl_no"):
                sequence_value = self.env["ir.sequence"].next_by_code(
                    "freight.sea.hbl.bl_no"
                ) or "1"
                vals["hbl_no"] = f"{month_value}/FCL-JKTPUS/{year_value}{int(sequence_value):03d}"
            if not vals.get("job_no"):
                sequence_value = self.env["ir.sequence"].next_by_code(
                    "freight.sea.hbl.job_no"
                ) or "1"
                vals["job_no"] = f"{month_value}/JOB-SHEET/{year_value}{int(sequence_value):03d}"
        return super().create(vals_list)
