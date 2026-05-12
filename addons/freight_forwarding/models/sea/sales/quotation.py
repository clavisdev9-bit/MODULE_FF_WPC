import base64
import os

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource


class SeaQuotation(models.Model):
    _name = "freight.sea.quotation"
    _inherit = "sale.order"
    _description = "Sea Quotation"
    _rec_name = "name"
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
        # "quotation_type",
        "container_type",
    )

    # Tambahin field ini buat narik data Booking yang terkait
    booking_ids = fields.One2many(
        "freight.sea.booking", "quotation_id", string="Sea Bookings"
    )

    # Field buat ngitung jumlah booking (buat nampilin angka di tombol)
    booking_count = fields.Integer(
        string="Booking Count", compute="_compute_booking_count"
    )

    # Field buat ngitung jumlah HBL (indirect melalui booking)
    hbl_count = fields.Integer(
        string="Jobsheet Count", compute="_compute_hbl_count"
    )

    @api.depends("booking_ids")
    def _compute_booking_count(self):
        for rec in self:
            rec.booking_count = len(rec.booking_ids)

    @api.depends("booking_ids.hbl_ids")
    def _compute_hbl_count(self):
        for rec in self:
            # Count HBL dari booking (export flow) + HBL langsung dari quotation (import flow)
            booking_hbls = sum(len(booking.hbl_ids) for booking in rec.booking_ids)
            direct_hbls = self.env["freight.sea.hbl"].search_count(
                [("quotation_id", "=", rec.id)]
            )
            rec.hbl_count = booking_hbls + direct_hbls

    # Fungsi pas smart button diklik
    def action_view_bookings(self):
        self.ensure_one()
        bookings = self.booking_ids

        # Buka form booking terkait
        return {
            "name": "Sea Booking",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            # Karena constraint lu 1 Quotation = 1 Booking, kita langsung buka form-nya
            "view_mode": "form" if len(bookings) == 1 else "list,form",
            "domain": [("id", "in", bookings.ids)],
            "res_id": bookings.id if len(bookings) == 1 else False,
            "context": dict(self.env.context, default_quotation_id=self.id),
        }

    def action_view_hbls(self):
        self.ensure_one()
        # Search HBL dari booking (export flow) OR langsung dari quotation (import flow)
        hbls = self.env["freight.sea.hbl"].search(
            ["|", ("booking_id.quotation_id", "=", self.id), ("quotation_id", "=", self.id)]
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

    def _sync_sale_order_rows(self):
        ids = self.ids
        query_filter = ""
        params = []
        if ids:
            query_filter = "WHERE q.id = ANY(%s)"
            params.append(ids)

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
            FROM freight_sea_quotation q
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
        return result

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

        # booking_type = "Export" if self.quotation_type == "export" else "Import"

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

        freight_type = "Export" if self.freight_type == "export" else "Import"
        
        # Create HBL directly linked to quotation (for import flow)
        hbl = self.env["freight.sea.hbl"].create(
            {
                "quotation_id": self.id,
                "freight_type": freight_type,
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

    # Left Side
    freight_type = fields.Selection(
        selection=[
            ("export", "Export"),
            ("import", "Import"),
        ],
        string="Quotation Type",
        required=True,
    )
    container_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Container Type",
        required=True,
    )
    quotation_title = fields.Char(string="Quotation Title")
    contact_person = fields.Char(
        string="Contact Person",
        compute="_compute_contact_person",
        store=False,
    )

    salesman_id = fields.Many2one(
        "hr.employee",
        string="Salesman",
    )

    phone = fields.Char(
        related="partner_id.phone",
        string="Phone",
        readonly=True,
    )
    email = fields.Char(
        related="partner_id.email", 
        string="Email",
        readonly=True
    )
    service_level = fields.Selection(
        [
            ("p1", "P1"),
            ("p2", "P2"),
            ("p3", "P3"),
            ("p4", "P4"),
        ],
        string="Service Level",
        default=False,
    )

    # Right Side
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist",
    )

    delivery_type_id = fields.Many2one(
        "freight.delivery.type",
        string="Delivery Type",
        required=True,
    )
    effective_date = fields.Date(string="Effective Date")
    expiry_date = fields.Date(string="Expiry Date")
    reference_number = fields.Char(string="Reference Number")
    commodity_id = fields.Many2one(
        "freight.commodity",
        string="Commodity",
        required=True,
    )

    # Address
    source_street = fields.Char(string="Source Street")
    source_street2 = fields.Char(string="Source Street 2")
    source_city = fields.Char(string="Source City")
    source_state_id = fields.Many2one(
        "res.country.state",
        string="Source State",
    )
    source_zip = fields.Char(string="Source Zip")
    source_country_id = fields.Many2one(
        "res.country",
        string="Source Country",
    )

    destination_street = fields.Char(string="Destination Street")
    destination_street2 = fields.Char(string="Destination Street 2")
    destination_city = fields.Char(string="Destination City")
    destination_state_id = fields.Many2one(
        "res.country.state",
        string="Destination State",
    )
    destination_zip = fields.Char(string="Destination Zip")
    destination_country_id = fields.Many2one(
        "res.country",
        string="Destination Country",
    )

    # Extra Info
    description_of_goods = fields.Char(string="Description of Goods")
    quantity = fields.Integer(string="Quantity")
    actual_weight = fields.Float(string="Actual Weight (Kg)")
    volume = fields.Float(string="Volume (Kg)")
    chargeable_weight = fields.Float(string="Chargeable Weight (Kg)")
    has_insurance = fields.Boolean(string="Has Insurance")
    insurance_id = fields.Many2one(
        "freight.insurance",
        string="Insurance",
    )

    # Dimension
    loose_quantity = fields.Integer(string="Loose Quantity")
    pcs = fields.Integer(string="PCS")
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unit of Measure",
    )
    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")
    dimension = fields.Float(string="Dimension")

    # Shipment Info
    port_of_loading_id = fields.Many2one(
        "freight.port", string="Port Of Loading"
    )

    port_of_discharge_id = fields.Many2one(
        "freight.port", string="Port Of Discharge"
    )

    via_port_id = fields.Many2one("freight.port", string="Via Port")

    origin_id = fields.Many2one("res.country.state", string="Origin")

    destination_id = fields.Many2one("res.country.state", string="Destination")

    via2_id = fields.Many2one("freight.port", string="Via2")

    via3_id = fields.Many2one("freight.port", string="Via3")

    shipping_line_id = fields.Many2one(
        "res.partner", 
        string="Shipping Line",
        domain="[('category_id.name', '=', 'Shipping Line')]"
    )

    est_transit_time_days = fields.Integer(string="Est. Transit Time (Days)", default=0)
    est_transit_time_note = fields.Char(string="Est. Transit Time Note")
    frequency = fields.Selection(
        selection=[
            ("weekly", "Weekly"),
            ("bi_weekly", "Bi-weekly"),
        ],
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
        "freight.terms.conditions",
        string="Terms and Condition",
    )
    description = fields.Text(
        related="terms_and_condition_id.description",
        string="Description")

    # Cargo Info
    cargo_info_ids = fields.One2many(
        "freight.sea.quotation.cargo.info",
        "quotation_id",
        string="Cargo Info",
    )

    # activity_type_id = fields.Many2one(
    #     "mail.activity.type",
    #     string="Activity Type",
    #     compute="_compute_activity_info",
    #     store=False,
    # )

    # activity_type_icon = fields.Char(
    #     string="Activity Type Icon",
    #     compute="_compute_activity_info",
    #     store=False,
    # )

    # activity_summary = fields.Char(
    #     string="Activity Summary",
    #     compute="_compute_activity_info",
    #     store=False,
    # )

    # @api.depends("activity_ids")
    # def _compute_activity_info(self):
    #     for rec in self:
    #         activities = rec.activity_ids.sorted(key=lambda a: a.date_deadline) if rec.activity_ids else self.env["mail.activity"]
    #         if activities:
    #             act = activities[0]
    #             rec.activity_type_id = act.activity_type_id or False
    #             rec.activity_type_icon = getattr(act, "icon", False) or False
    #             rec.activity_summary = getattr(act, "summary", False) or False
    #         else:
    #             rec.activity_type_id = False
    #             rec.activity_type_icon = False
    #             rec.activity_summary = False

    def get_report_logo_src(self):
        logo_path = get_module_resource(
            "freight_forwarding", "static", "description", "logo.png"
        )
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return "data:image/png;base64," + encoded
        return ""
