import base64
import os

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource


class FreightQuotation(models.AbstractModel):
    """
    Abstract mixin untuk semua jenis Quotation (Sea, Air, dll).
    Berisi field dan method yang sama di semua jenis quotation.

    Subclass WAJIB mendefinisikan:
        _quotation_table = "nama_tabel_db"        (str)
        _SALE_ORDER_SYNC_COLUMNS = (...)          (tuple of str)
    """

    _name = "freight.quotation"
    _description = "Freight Quotation Mixin"

    # =========================================================
    # Common Fields
    # =========================================================

    # Header
    freight_type = fields.Selection(
        selection=[
            ("export", "Export"),
            ("import", "Import"),
        ],
        string="Quotation Type",
        required=True,
    )
    quotation_title = fields.Char(string="Quotation Title")
    contact_person = fields.Char(
        string="Contact Person",
        compute="_compute_contact_person",
        store=False,
    )
    salesman_id = fields.Many2one("hr.employee", string="Salesman")
    partner_id = fields.Many2one("res.partner", string="Customer")
    phone = fields.Char(related="partner_id.phone", string="Phone", readonly=True)
    email = fields.Char(related="partner_id.email", string="Email", readonly=True)

    service_level = fields.Selection(
        [("p1", "P1"), ("p2", "P2"), ("p3", "P3"), ("p4", "P4")],
        string="Service Level",
        default=False,
    )

    # Right side header
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist")
    delivery_type_id = fields.Many2one(
        "freight.delivery.type", string="Delivery Type", required=True
    )
    effective_date = fields.Date(string="Effective Date")
    # validity_date = fields.Date(string="Expiry Date")
    reference_number = fields.Char(string="Reference Number")
    commodity_id = fields.Many2one(
        "freight.commodity", string="Commodity", required=True
    )

    # Address — Source
    source_street = fields.Char(string="Source Street")
    source_street2 = fields.Char(string="Source Street 2")
    source_city = fields.Char(string="Source City")
    source_state_id = fields.Many2one("res.country.state", string="Source State")
    source_zip = fields.Char(string="Source Zip")
    source_country_id = fields.Many2one("res.country", string="Source Country")

    # Address — Destination
    destination_street = fields.Char(string="Destination Street")
    destination_street2 = fields.Char(string="Destination Street 2")
    destination_city = fields.Char(string="Destination City")
    destination_state_id = fields.Many2one("res.country.state", string="Destination State")
    destination_zip = fields.Char(string="Destination Zip")
    destination_country_id = fields.Many2one("res.country", string="Destination Country")

    # Extra Info
    description_of_goods = fields.Char(string="Description of Goods")
    quantity = fields.Integer(string="Quantity")
    actual_weight = fields.Float(string="Actual Weight (Kg)")
    volume = fields.Float(string="Volume (Kg)")
    chargeable_weight = fields.Float(string="Chargeable Weight (Kg)")
    has_insurance = fields.Boolean(string="Has Insurance")
    insurance_id = fields.Many2one("freight.insurance", string="Insurance")

    # Dimension
    loose_quantity = fields.Integer(string="Loose Quantity")
    pcs = fields.Integer(string="PCS")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")
    dimension = fields.Float(string="Dimension")

    # Shipment Info — Common
    origin_id = fields.Many2one("res.city", string="Origin")
    destination_id = fields.Many2one("res.city", string="Destination")
    est_transit_time_days = fields.Integer(
        string="Est. Transit Time (Days)", default=0
    )
    est_transit_time_note = fields.Char(string="Est. Transit Time Note")
    frequency = fields.Selection(
        selection=[("weekly", "Weekly"), ("bi_weekly", "Bi-weekly")],
        string="Frequency",
    )
    frt_collect = fields.Selection(
        selection=[("Y", "Collect"), ("N", "Prepaid")],
        string="FRT Collect",
        default="N",
    )
    note = fields.Text(string="Note")

    # Header & Footer
    header = fields.Char(string="Header")
    special_instruction = fields.Text(string="Special Instruction")
    footer = fields.Char(string="Footer")

    # Terms and Condition
    terms_and_condition_id = fields.Many2one(
        "freight.terms.conditions", string="Terms and Condition"
    )
    description = fields.Text(
        related="terms_and_condition_id.description", string="Description"
    )

    # =========================================================
    # Common Methods
    # =========================================================

    def _compute_tasks_ids(self):
        for rec in self:
            rec.tasks_ids = False
            rec.tasks_count = 0
            rec.closed_task_count = 0

    @api.depends("partner_id.child_ids")
    def _compute_contact_person(self):
        for rec in self:
            children = (
                rec.partner_id.child_ids if rec.partner_id else self.env["res.partner"]
            )
            rec.contact_person = children[0].name if children else False

    @api.constrains("est_transit_time_days")
    def _check_est_transit_time_days(self):
        for record in self:
            if record.est_transit_time_days < 0:
                raise ValidationError("Est. Transit Time (Days) cannot be negative.")

    def _sync_sale_order_rows(self):
        """
        Sync baris dari tabel quotation masing-masing ke sale_order.
        Subclass wajib mendefinisikan _quotation_table dan _SALE_ORDER_SYNC_COLUMNS.

        Catatan arsitektur: menggunakan raw SQL (bukan ORM) karena sale_order
        adalah tabel Odoo bawaan yang tidak bisa di-inherit secara langsung.
        Setelah raw INSERT, cache ORM di-invalidate secara eksplisit.
        """
        ids = self.ids
        query_filter = ""
        params = []
        if ids:
            query_filter = "WHERE q.id = ANY(%s)"
            params.append(ids)

        table = self._quotation_table
        columns = ", ".join(self._SALE_ORDER_SYNC_COLUMNS)
        select_columns = ", ".join(
            f"q.{column}" for column in self._SALE_ORDER_SYNC_COLUMNS
        )
        update_columns = ", ".join(
            f"{column} = EXCLUDED.{column}" for column in self._SALE_ORDER_SYNC_COLUMNS
        )

        self.env.cr.execute(
            f"""
            INSERT INTO sale_order (id, {columns})
            SELECT q.id, {select_columns}
            FROM {table} q
            {query_filter}
            ON CONFLICT (id)
            DO UPDATE SET {update_columns}
            """,
            params,
        )
        self.env.cr.execute(
            """
            SELECT setval(
                'sale_order_id_seq',
                (SELECT COALESCE(MAX(id), 1) FROM sale_order),
                TRUE
            )
            """
        )
        # Invalidate ORM cache agar data yang baru di-sync terbaca dengan benar
        self.env["sale.order"].invalidate_model()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_sale_order_rows()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._sync_sale_order_rows()
        return result

    def unlink(self):
        ids = self.ids
        result = super().unlink()
        if ids:
            self.env.cr.execute("DELETE FROM sale_order WHERE id = ANY(%s)", [ids])
            # Invalidate cache setelah raw DELETE
            self.env["sale.order"].invalidate_model()
        return result

    def get_report_logo_src(self):
        logo_path = get_module_resource(
            "freight_forwarding", "static", "description", "logo.png"
        )
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return "data:image/png;base64," + encoded
        return ""
