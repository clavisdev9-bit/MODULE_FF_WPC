import base64
import os

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
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

    is_freight_quotation = fields.Boolean(string="Is Freight Quotation", default=False)

    # =========================================================
    # Header Information
    # =========================================================

    # Left side header
    freight_business_type = fields.Selection(
        selection=[
            ("sea", "Sea"),
            ("air", "Air"),
        ],
        string="Freight Business Type",
    )
    freight_type = fields.Selection(
        selection=[
            ("export", "Export"),
            ("import", "Import"),
        ],
        string="Quotation Type",
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
        "freight.delivery.type", string="Delivery Type"
    )
    valid_from = fields.Date(string="Valid From")
    # validity_date = fields.Date(string="Valid To")
    reference_number = fields.Char(string="Reference Number")
    commodity_id = fields.Many2one(
        "freight.commodity", string="Commodity"
    )

    # Address — Source
    pickup_street = fields.Char(string="Pickup Street")
    pickup_street2 = fields.Char(string="Pickup  Street 2")
    pickup_city = fields.Many2one("res.city", string="Pickup  City")
    pickup_state_id = fields.Many2one("res.country.state", string="Pickup  State")
    pickup_zip = fields.Char(string="Pickup  Zip")
    pickup_country_id = fields.Many2one("res.country", string="Pickup  Country")

    # Address — Destination
    delivery_street = fields.Char(string="Delivery Street")
    delivery_street2 = fields.Char(string="Delivery Street 2")
    delivery_city = fields.Many2one("res.city", string="Delivery City")
    delivery_state_id = fields.Many2one("res.country.state", string="Delivery State")
    delivery_zip = fields.Char(string="Delivery Zip")
    delivery_country_id = fields.Many2one("res.country", string="Delivery Country")

    @api.onchange("pickup_city")
    def _onchange_pickup_city(self):
        city = self.pickup_city
        if not city:
            return
        if city.zipcode:
            self.pickup_zip = city.zipcode
        if city.state_id:
            self.pickup_state_id = city.state_id
        if city.country_id:
            self.pickup_country_id = city.country_id

    @api.onchange("delivery_city")
    def _onchange_delivery_city(self):
        city = self.delivery_city
        if not city:
            return
        if city.zipcode:
            self.delivery_zip = city.zipcode
        if city.state_id:
            self.delivery_state_id = city.state_id
        if city.country_id:
            self.delivery_country_id = city.country_id

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
    est_transit_time_days = fields.Integer(string="Est. Transit Time (Days)", default=0)
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
    terms_and_conditions = fields.Text(string="Terms & Conditions")

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

    @api.constrains("is_freight_quotation", "freight_type", "delivery_type_id", "commodity_id")
    def _check_freight_quotation_required_fields(self):
        """freight_type/delivery_type_id/commodity_id hanya wajib untuk Freight Quotation,
        agar tidak memblokir pembuatan Sales Order normal (bukan Freight) di sale.order."""
        for record in self:
            if not record.is_freight_quotation:
                continue
            missing = []
            if not record.freight_type:
                missing.append("Quotation Type")
            if not record.delivery_type_id:
                missing.append("Delivery Type")
            if not record.commodity_id:
                missing.append("Commodity")
            if missing:
                raise ValidationError(
                    "%s is required for a Freight Quotation." % ", ".join(missing)
                )

    def _has_downstream_quotation_records(self):
        """True jika quotation ini sudah punya Booking/Jobsheet turunan
        (Sea maupun Air) — dipakai untuk mengunci perubahan direction."""
        self.ensure_one()
        return bool(
            self.booking_count
            or self.hbl_count
            or getattr(self, "air_booking_count", 0)
            or getattr(self, "hawb_count", 0)
        )

    def action_convert_quotation(self):
        """Satu entry point publik untuk convert quotation ke downstream
        record; branching Import/Export ditangani di sini, bukan lewat
        dua button/action terpisah (lihat FF-71)."""
        self.ensure_one()
        if not self.is_freight_quotation:
            raise UserError(
                "This action is only available for a Freight Quotation."
            )
        if self.freight_type == "import":
            return self.action_convert_to_jobsheet_direct()
        return self.action_convert_to_booking_direct()

    def action_convert_to_booking_direct(self):
        """Dispatch eksplisit berdasarkan freight_business_type, bukan
        lewat urutan _inherit/super() antar modul air & sea — supaya tidak
        diam-diam salah pilih implementasi kalau urutan import berubah."""
        self.ensure_one()
        if self.freight_business_type == "air":
            return self._action_convert_to_booking_direct_air()
        return self._action_convert_to_booking_direct_sea()

    def action_convert_to_jobsheet_direct(self):
        """Dispatch eksplisit berdasarkan freight_business_type — lihat
        action_convert_to_booking_direct."""
        self.ensure_one()
        if self.freight_business_type == "air":
            return self._action_convert_to_jobsheet_direct_air()
        return self._action_convert_to_jobsheet_direct_sea()

    def _sync_sale_order_rows(self):
        """
        Sync baris dari tabel quotation masing-masing ke sale_order.
        Subclass wajib mendefinisikan _quotation_table dan _SALE_ORDER_SYNC_COLUMNS.

        Catatan arsitektur: menggunakan raw SQL (bukan ORM) karena sale_order
        adalah tabel Odoo bawaan yang tidak bisa di-inherit secara langsung.
        Setelah raw INSERT, cache ORM di-invalidate secara eksplisit.
        """
        if self._name == "sale.order":
            return
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

        # Perbaiki issue currency di order_line (sale.order.line)
        # Karena INSERT/UPDATE ke sale_order di atas menggunakan raw SQL,
        # ORM tidak mendeteksi perubahan dan tidak me-recompute related field (currency_id) di line.
        # Kita update langsung di DB agar sinkron.
        if ids:
            self.env.cr.execute(
                """
                UPDATE sale_order_line sol
                SET currency_id = so.currency_id
                FROM sale_order so
                WHERE sol.order_id = so.id 
                  AND so.id = ANY(%s) 
                  AND (sol.currency_id != so.currency_id OR sol.currency_id IS NULL)
                """,
                [ids],
            )

        # Invalidate ORM cache agar data yang baru di-sync terbaca dengan benar
        self.env["sale.order"].invalidate_model()
        self.env["sale.order.line"].invalidate_model(["currency_id"])

    def copy(self, default=None):
        """
        Override copy() untuk:
        1. Preserve validity_date (Expiry Date) dari record sumber.
           Tanpa ini, saat duplicate Odoo me-reset date_order ke hari ini
           sehingga validity_date ikut recalculate → beda dari aslinya.
        2. Menyelesaikan issue "Missing Record" saat menduplikasi order_line.
           Karena order_line divalidasi ke tabel sale_order, kita menunda
           duplikasi order_line sampai setelah record disinkronisasi ke sale_order.
        """
        if self._name == "sale.order":
            return super().copy(default=default)
            
        default = dict(default or {})
        # Salin validity_date dari source agar tidak di-recalculate
        if "validity_date" not in default and self.validity_date:
            default["validity_date"] = self.validity_date

        # Tunda duplikasi order_line dari ORM bawaan
        copy_order_lines = False
        if "order_line" not in default:
            default["order_line"] = False
            copy_order_lines = True
        elif not default["order_line"]:
            # [] atau None dari caller (misal action_create_currency_variant) tidak cukup untuk
            # suppress copying di Odoo ORM — normalize ke False agar lines tidak ikut ter-copy.
            default["order_line"] = False

        new_record = super().copy(default=default)
        new_record._sync_sale_order_rows()

        # Setelah record disinkronisasi ke tabel sale_order, barulah aman menduplikasi order_line
        if copy_order_lines and self.order_line:
            for line in self.order_line:
                line.copy({"order_id": new_record.id})

        return new_record

    @api.model_create_multi
    def create(self, vals_list):
        if self._name == "sale.order":
            return super().create(vals_list)
        records = super().create(vals_list)
        # Flush deferred computed fields (e.g. currency_id dari pricelist_id) ke DB
        # sebelum raw SQL sync, agar _sync_sale_order_rows tidak baca nilai stale.
        records.flush_recordset()
        records._sync_sale_order_rows()
        return records

    def write(self, vals):
        if "freight_type" in vals:
            for rec in self:
                if (
                    rec.is_freight_quotation
                    and rec.freight_type
                    and vals["freight_type"] != rec.freight_type
                    and rec._has_downstream_quotation_records()
                ):
                    raise UserError(
                        "Quotation Type (Import/Export) cannot be changed anymore: "
                        "this quotation already has a Booking or Jobsheet linked to it."
                    )
        if self._name == "sale.order":
            return super().write(vals)
        result = super().write(vals)
        # Flush deferred computed fields sebelum sync — lihat FF-19.
        self.flush_recordset()
        self._sync_sale_order_rows()
        return result

    def unlink(self):
        if self._name == "sale.order":
            return super().unlink()
        ids = self.ids
        result = super().unlink()
        if ids:
            self.env.cr.execute("DELETE FROM sale_order WHERE id = ANY(%s)", [ids])
            # Invalidate cache setelah raw DELETE
            self.env["sale.order"].invalidate_model()
        return result

    def _get_sea_hbl_analytic_account(self):
        self.ensure_one()
        if hasattr(self, "sea_hbl_id") and self.sea_hbl_id and self.sea_hbl_id.analytic_account_id:
            return self.sea_hbl_id.analytic_account_id
        hbl = self.env["freight.sea.hbl"].search([("sale_order_ids", "=", self.id)], limit=1)
        if hbl and hbl.analytic_account_id:
            return hbl.analytic_account_id
        if self.env.context.get("default_sea_hbl_id"):
            hbl = self.env["freight.sea.hbl"].browse(self.env.context.get("default_sea_hbl_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if hasattr(self, "sea_hbl_id") and self.sea_hbl_id:
            invoice_vals["sea_hbl_id"] = self.sea_hbl_id.id
        else:
            hbl = self.env["freight.sea.hbl"].search([("sale_order_ids", "=", self.id)], limit=1)
            if hbl:
                invoice_vals["sea_hbl_id"] = hbl.id
        return invoice_vals

    def get_report_logo_src(self):
        logo_path = get_module_resource(
            "freight_forwarding", "static", "description", "logo.png"
        )
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return "data:image/png;base64," + encoded
        return ""


class SaleOrderQuotation(models.Model):
    """Satu-satunya tempat yang menempelkan mixin freight.quotation ke
    sale.order. SeaQuotation dan AirQuotation (models/sea|air/sales/quotation.py)
    sengaja hanya _inherit = "sale.order" (plain) — tidak ada satupun dari
    keduanya yang perlu tahu soal mixin ini (lihat FF-71 structural cleanup).

    Class ini juga menampung fitur currency-variant: generik, tidak menyentuh
    field sea-specific maupun air-specific apa pun, dan sudah dipakai oleh
    view Air maupun Sea.
    """

    _name = "sale.order"
    _inherit = ["sale.order", "freight.quotation"]

    original_quotation_id = fields.Many2one(
        "sale.order",
        string="Original Quotation",
        copy=False,
        index=True,
    )
    variant_ids = fields.One2many(
        "sale.order",
        "original_quotation_id",
        string="Currency Variants",
    )
    variant_count = fields.Integer(
        string="Variant Count",
        compute="_compute_variant_count",
    )

    @api.depends("variant_ids", "original_quotation_id.variant_ids")
    def _compute_variant_count(self):
        for rec in self:
            root = rec.original_quotation_id if rec.original_quotation_id else rec
            rec.variant_count = len(root.variant_ids)

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


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_sea_hbl_analytic_account(self):
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_sea_hbl_analytic_account"):
            acc = self.order_id._get_sea_hbl_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_sea_hbl_id"):
            hbl = self.env["freight.sea.hbl"].browse(self.env.context.get("default_sea_hbl_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    @api.depends("product_id", "order_id.sea_hbl_id")
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if not line.analytic_distribution and line.display_type not in ("line_section", "line_note"):
                analytic_account = line._get_sea_hbl_analytic_account()
                if analytic_account:
                    line.analytic_distribution = {str(analytic_account.id): 100.0}

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        if not res.get("analytic_distribution"):
            analytic_account = self._get_sea_hbl_analytic_account()
            if analytic_account:
                res["analytic_distribution"] = {str(analytic_account.id): 100.0}
        return res

