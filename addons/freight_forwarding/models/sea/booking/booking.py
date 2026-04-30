from odoo import fields, models

class SeaBooking(models.Model):
    _name = "freight.sea.booking"
    _description = "Sea Booking"
    _rec_name = "name"

    _sql_constraints = [
        (
            "quotation_id_unique",
            "unique(quotation_id)",
            "Quotation No. already exists on another Sea Booking.",
        )
    ]

    # Header Information
    type = fields.Selection(
        selection=[
            ("Import", "Import"),
            ("Export", "Export"),
        ],
        string="Type",
        required=True,
    )
    name = fields.Char(string="Booking No.", required=True, copy=False)
    booking_date = fields.Datetime(string="Date & Time")
    bl_no = fields.Char(string="B/L No.")
    job_no = fields.Char(string="Job No.")
    nomination_cargo = fields.Boolean(string="Nomination Cargo")
    freight_type = fields.Selection(
        selection=[("fcl", "FCL"), ("lcl", "LCL"), ("consol", "Consol")],
        string="Freight Type",
        required=True,
    )
    job_date = fields.Date(string="Job Date")
    import_job_no = fields.Char(string="Import Job Number (Optional)")
    railing = fields.Boolean(string="Railing")

    # Customer & Contact Data
    customer_id = fields.Many2one(
        "res.partner", 
        string="Customer Name",
        domain="[('category_id.name', '=', 'Customer')]",
        required=True
    )
    customer_reference = fields.Char(string="Customer Reference")
    phone = fields.Char(related="customer_id.phone", string="Phone Number")
    email = fields.Char(related="customer_id.email", string="Email Address")
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Terms of Payment",
    )
    salesman_id = fields.Many2one(
        "res.partner", 
        string="Salesman",
        domain="[('category_id.name', '=', 'Salesman')]"
    )
    quotation_id = fields.Many2one(
        "freight.sea.quotation",
        string="Quotation No.",
        ondelete="set null",
        readonly=True,
    )

    # Shipment Details
    origin_port_id = fields.Many2one(
        "freight.port", string="Origin Port Code (POL)"
    )
    destination_port_id = fields.Many2one(
        "freight.port", string="Destination Port Code (POD)"
    )
    etd = fields.Date(string="ETD (Departure)")
    eta = fields.Date(string="ETA (Arrival)")
    destination_country_id = fields.Many2one(
        "res.country", string="Destination Country"
    )
    cargo_origin_country_id = fields.Many2one(
        "res.country", string="Cargo Origin Country (Optional)"
    )
    delivery_type_id = fields.Many2one(
        "freight.delivery.type", string="Delivery Type", required=True
    )

    # Vessel Information
    pod_port_id = fields.Many2one("freight.port", string="Port of Discharge")
    vessel_id = fields.Many2one("freight.vessel", string="Vessel Name")
    voyage_no = fields.Char(string="Voyage No.")
    eta_jkt = fields.Date(string="ETA on JKT")

    # Notebook
    cargo_info_ids = fields.One2many(
        "freight.sea.booking.cargo.info",
        "booking_id",
        string="Cargo Info",
    )
    sea_bl_info_ids = fields.One2many(
        "freight.sea.booking.bl.info",
        "booking_id",
        string="Sea B/L Info",
    )
    pickup_info_ids = fields.One2many(
        "freight.sea.booking.pickup.info",
        "booking_id",
        string="Pickup Info",
    )
    shipment_info_ids = fields.One2many(
        "freight.sea.booking.shipment.info",
        "booking_id",
        string="Shipment Info",
    )
    vessel_details_ids = fields.One2many(
        "freight.sea.booking.vessel.details",
        "booking_id",
        string="Vessel Details",
    )
    purchase_order_ids = fields.One2many(
        "freight.sea.booking.purchase.order",
        "booking_id",
        string="Sea Purchase Order",
    )
    notify_party_line_ids = fields.One2many(
        "freight.sea.booking.notify.party",
        "booking_id",
        string="Notify Party",
    )
    extra_info_ids = fields.One2many(
        "freight.sea.booking.extra.info",
        "booking_id",
        string="Extra Info",
    )

    def action_add_notify_party(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Add Notify Party",
            "res_model": "freight.sea.booking.notify.party",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_booking_id": self.id,
            },
        }

    def action_view_notify_party(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Notify Party",
            "res_model": "freight.sea.booking.notify.party",
            "view_mode": "list,form",
            "domain": [("booking_id", "=", self.id)],
            "context": {
                "default_booking_id": self.id,
            },
            "target": "current",
        }

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
        hbl_items_model = self.env["freight.sea.hbl.items.line"]

        for booking_cargo_info in booking_cargo_info_records:
            cargo_values = booking_cargo_info.copy_data(default={"hbl_id": hbl.id})[0]
            for field_name in ["booking_id", "quotation_id", "freight_items_line"]:
                cargo_values.pop(field_name, None)
            for field_name in list(cargo_values.keys()):
                if field_name not in hbl_cargo_model._fields:
                    cargo_values.pop(field_name, None)
            cargo_values["hbl_id"] = hbl.id
            hbl_cargo = hbl_cargo_model.create(cargo_values)

            for booking_item_line in booking_cargo_info.freight_items_line:
                item_values = booking_item_line.copy_data(default={"hbl_cargo_info_id": hbl_cargo.id})[0]
                for field_name in ["booking_cargo_info_id"]:
                    item_values.pop(field_name, None)
                for field_name in list(item_values.keys()):
                    if field_name not in hbl_items_model._fields:
                        item_values.pop(field_name, None)
                item_values["hbl_cargo_info_id"] = hbl_cargo.id
                hbl_items_model.create(item_values)

    def _copy_booking_data_to_hbl(self, booking, hbl):
        if not hbl.shipment_info_ids and booking.shipment_info_ids:
            self._copy_records_to_hbl(
                booking.shipment_info_ids,
                "freight.sea.hbl.shipment.info",
                "hbl_id",
                extra_values={"hbl_id": hbl.id},
                excluded_fields={"booking_id"},
            )

        if not hbl.vessel_details_ids and booking.vessel_details_ids:
            self._copy_records_to_hbl(
                booking.vessel_details_ids,
                "freight.sea.hbl.vessel.details",
                "hbl_id",
                extra_values={"hbl_id": hbl.id},
                excluded_fields={"booking_id"},
            )

        if not hbl.cargo_info_ids and booking.cargo_info_ids:
            self._copy_cargo_info_lines_to_hbl(booking.cargo_info_ids, hbl)

        if not hbl.purchase_order_ids and booking.purchase_order_ids:
            self._copy_records_to_hbl(
                booking.purchase_order_ids,
                "freight.sea.hbl.purchase.order",
                "hbl_id",
                extra_values={"hbl_id": hbl.id},
                excluded_fields={"booking_id"},
            )

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
                    "type": self.type,
                    "freight_type": self.freight_type,
                    "customer_id": self.customer_id.id,
                    "term_payment": self.payment_term_id.id,
                    "job_date": self.job_date,
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