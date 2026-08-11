from odoo import api, fields, models


class SeaBooking(models.Model):
    _name = "freight.sea.booking"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "freight.sea.shipment.info.mixin",
        "freight.sea.vessel.details.mixin",
        "freight.sea.bl.info.mixin",
    ]
    _description = "Sea Booking"
    _rec_name = "name"



    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )

    # Field relasi narik data Jobsheet (HBL) yang terkait sama Booking ini
    hbl_ids = fields.One2many("freight.sea.hbl", "booking_id", string="Sea Jobsheets")

    # Field count buat trigger sembunyi/tampil tombol
    hbl_count = fields.Integer(string="Jobsheet Count", compute="_compute_hbl_count")

    # Field buat show quotation (one-to-many relationship)
    sales_order_count = fields.Integer(
        string="Sales Order Count", compute="_compute_sales_order_count"
    )

    @api.depends("hbl_ids")
    def _compute_hbl_count(self):
        for rec in self:
            rec.hbl_count = len(rec.hbl_ids)

    @api.depends("sale_order_ids")
    def _compute_sales_order_count(self):
        for rec in self:
            rec.sales_order_count = len(rec.sale_order_ids)



    @api.onchange("from_city")
    def _onchange_from_city(self):
        for rec in self:
            if rec.from_city.country_id:
                rec.origin_country_id = rec.from_city.country_id

    @api.onchange("to_city")
    def _onchange_to_city(self):
        for rec in self:
            rec.destination_country_id = rec.to_city.country_id

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            rec.state = "draft"

    # Fungsi pas tombol Jobsheet di klik
    def action_view_hbl(self):
        self.ensure_one()
        hbls = self.hbl_ids

        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context, default_booking_id=self.id, default_company_id=self.company_id.id),
        }

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
    name = fields.Char(
        string="Booking No.",
        required=True,
        default=lambda self: "New",
        copy=False,
    )
    booking_date = fields.Datetime(string="Date & Time")
    bl_no = fields.Char(string="B/L No.")
    job_no = fields.Char(string="Job No.")
    nomination_cargo = fields.Boolean(string="Nomination Cargo")
    container_type = fields.Selection(
        selection=[("fcl", "FCL"), ("lcl", "LCL"), ("consol", "Consol")],
        string="Container Type",
        required=True,
    )
    job_date = fields.Date(string="Job Date")
    import_job_no = fields.Char(string="Import Job Number (Optional)")
    railing = fields.Boolean(string="Railing")

    # Customer & Contact Data
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer Name",
        required=True,
    )
    customer_reference = fields.Char(string="Customer Reference")
    phone = fields.Char(related="partner_id.phone", string="Phone Number")
    email = fields.Char(related="partner_id.email", string="Email Address")
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
    )
    salesman_id = fields.Many2one(
        "hr.employee",
        string="Salesman",
    )
    sale_order_ids = fields.Many2many(
        "sale.order",
        string="Sales Orders",
    )

    # Shipment Details
    # NOTE (FF-22): port_of_loading_id, port_of_discharge_id, commodity_id,
    # dan eta_jkt juga ada di freight.sea.shipment.info.mixin. Karena Booking
    # sudah mendefinisikan field ini sendiri (dengan required=True dan string
    # custom), definisi di sini yang dipakai. Field ini TIDAK ditambahkan lagi
    # di tab "Shipment Details"/"Vessel Schedule" baru supaya tidak duplikat
    # di view.
    port_of_loading_id = fields.Many2one(
        "freight.port", string="Origin Port (POL)", required=True
    )
    port_of_discharge_id = fields.Many2one(
        "freight.port", string="Destination Port (POD)", required=True
    )
    etd = fields.Date(string="ETD (Departure)")
    eta = fields.Date(string="ETA (Arrival)")
    destination_country_id = fields.Many2one(
        "res.country", string="Destination Country"
    )
    origin_country_id = fields.Many2one(
        "res.country", string="Origin Country"
    )
    from_city = fields.Many2one("res.city", string="From")
    to_city = fields.Many2one("res.city", string="To")
    delivery_type_id = fields.Many2one(
        "freight.delivery.type", string="Delivery Type", required=True
    )
    commodity_id = fields.Many2one("freight.commodity", string="Commodity")

    # Vessel Information
    pod_port_id = fields.Many2one("freight.port", string="Port of Delivery")
    vessel_id = fields.Many2one("freight.vessel", string="Vessel Name", required=True)
    voyage_no = fields.Char(string="Voyage No.")
    eta_jkt = fields.Date(string="ETA on JKT")

    # Notebook
    # NOTE (FF-22): field shipment_info_ids (One2many ke
    # freight.sea.booking.shipment.info) DIHAPUS. Model perantaranya sudah
    # dihapus; field-fieldnya sekarang ada langsung di sini lewat
    # freight.sea.shipment.info.mixin (lihat _inherit di atas).
    cargo_info_ids = fields.One2many(
        "freight.sea.booking.cargo.info",
        "booking_id",
        string="Cargo Info",
    )

    purchase_order_ids = fields.Many2many(
        "purchase.order",
        string="Purchase Orders",
    )
    extra_info_ids = fields.One2many(
        "freight.sea.booking.extra.info",
        "booking_id",
        string="Extra Info",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "freight.sea.booking"
                ) or "New"
        return super().create(vals_list)

    def _copy_records_to_hbl(self, source_records, target_model_name, target_field_name, extra_values=None, excluded_fields=None):
        target_model = self.env[target_model_name]
        excluded_fields = set(excluded_fields or [])
        extra_values = extra_values or {}

        for source_record in source_records:
            values = source_record.copy_data(default=extra_values)[0]
            for field_name in list(values.keys()):
                if field_name in excluded_fields or field_name not in target_model._fields:
                    values.pop(field_name, None)
            values[target_field_name] = extra_values[target_field_name]
            target_model.create(values)

    def _copy_cargo_info_lines_to_hbl(self, booking_cargo_info_records, hbl):
        hbl_cargo_model = self.env["freight.sea.hbl.cargo.info"]

        for booking_cargo_info in booking_cargo_info_records:
            cargo_values = booking_cargo_info.copy_data(default={"hbl_id": hbl.id})[0]
            for field_name in ["booking_id", "sale_order_ids"]:
                cargo_values.pop(field_name, None)
            for field_name in list(cargo_values.keys()):
                if field_name not in hbl_cargo_model._fields:
                    cargo_values.pop(field_name, None)
            cargo_values["hbl_id"] = hbl.id
            hbl_cargo_model.create(cargo_values)

    def _copy_booking_data_to_hbl(self, booking, hbl):
        # NOTE (FF-22): pemanggilan copy shipment_info_ids DIHAPUS di sini
        # karena model freight.sea.booking.shipment.info /
        # freight.sea.hbl.shipment.info sudah tidak ada. Field-field
        # shipment info sekarang langsung ada di Booking & HBL (lewat mixin),
        # jadi tidak perlu proses copy antar model perantara lagi.


        vessel_fields = [
            "principle_agent_id", "shipping_agent_id", "scn_code", "warehouse_id",
            "smk_code1", "smk_code2", "close_date", "cargo_receipt_date",
            "stuffing_date", "contact_id", "yard_id", "depot_id",
            "depot_instruction", "general_instruction"
        ]
        hbl_update = {}
        for field in vessel_fields:
            if not hbl[field] and booking[field]:
                val = booking[field]
                hbl_update[field] = val.id if hasattr(val, 'id') else val
        if hbl_update:
            hbl.write(hbl_update)

        if not hbl.sale_order_ids and booking.sale_order_ids:
            hbl.write({"sale_order_ids": [(6, 0, booking.sale_order_ids.ids)]})

        if not hbl.cargo_info_ids and booking.cargo_info_ids:
            self._copy_cargo_info_lines_to_hbl(booking.cargo_info_ids, hbl)

        if not hbl.purchase_order_ids and booking.purchase_order_ids:
            hbl.write({"purchase_order_ids": [(6, 0, booking.purchase_order_ids.ids)]})

    def action_convert_to_hbl(self):
        self.ensure_one()

        existing_hbl = self.env["freight.sea.hbl"].search(
            [("booking_id", "=", self.id)],
            limit=1,
            order="id desc",
        )
        if existing_hbl:
            hbl = existing_hbl
        else:
            hbl = self.env["freight.sea.hbl"].create(
                {
                    "booking_id": self.id,
                    "freight_type": self.freight_type,
                    "container_type": self.container_type,
                    "customer_id": self.partner_id.id,
                    "term_payment": self.payment_term_id.id,
                    "job_date": self.job_date,
                    "master_job_no": self.job_no,
                    "salesman_id": self.salesman_id.id if self.salesman_id else False,
                }
            )

        self._copy_booking_data_to_hbl(self, hbl)

        return {
            "type": "ir.actions.act_window",
            "name": "Sea Jobsheet",
            "res_model": "freight.sea.hbl",
            "res_id": hbl.id,
            "view_mode": "form",
            "target": "current",
        }