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
        "transportation_method",
        "quotation_type",
        "freight_type",
    )

    def init(self):
        self.sudo().search([])._sync_sale_order_rows()

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
    quotation_type = fields.Selection(
        selection=[
            ("export", "Export"),
            ("import", "Import"),
        ],
        string="Quotation Type",
        required=True,
    )
    freight_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Freight Type",
        required=True,
    )
    quotation_title = fields.Char(string="Quotation Title")
    contact_person = fields.Char(
        related="partner_id.child_ids.name",
        string="Contact Person"
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
    quantity = fields.Float(string="Quantity")
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

    origin_id = fields.Many2one("freight.location", string="Origin")

    destination_id = fields.Many2one("freight.location", string="Destination")

    via2_id = fields.Many2one("freight.port", string="Via2")

    via3_id = fields.Many2one("freight.port", string="Via3")

    shipping_line_id = fields.Many2one(
        "freight.carrier", string="Shipping Line"
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

    @api.constrains("est_transit_time_days")
    def _check_est_transit_time_days(self):
        for record in self:
            if record.est_transit_time_days < 0:
                raise ValidationError("Est. Transit Time (Days) cannot be negative.")

    def _prepare_booking_cargo_info_vals(self, cargo_info, booking):
        return {
            "booking_id": booking.id,
            "package_type": cargo_info.package_type,
            "size_package": cargo_info.size_package.id,
            "container_no": cargo_info.container_no,
            "stamp_no": cargo_info.stamp_no,
            "container_box_type_id": cargo_info.container_box_type_id.id,
            "types_of_cargo": cargo_info.types_of_cargo.id,
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

        booking_no = self.env["ir.sequence"].next_by_code(
            "freight.sea.booking"
        ) or fields.Date.today().strftime("WPCS%d%m-001")

        booking_type = "Export" if self.quotation_type == "export" else "Import"

        booking_vals = {
            "name": booking_no,
            "quotation_id": self.id,
            "customer_id": self.partner_id.id,
            "delivery_type_id": self.delivery_type_id.id,
            "origin_port_id": self.port_of_loading_id.id,
            "destination_port_id": self.port_of_discharge_id.id,
            "destination_country_id": destination_country.id if destination_country else False,
            "cargo_origin_country_id": origin_country.id if origin_country else False,
            "phone": self.phone,
            "email": self.email,
            "salesman_id": self.user_id.id,
            "payment_term_id": self.payment_term_id.id,
            "freight_type": self.freight_type,
            "type": booking_type,
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

    # Header & Footer
    header = fields.Char(string="Header")
    special_instruction = fields.Text(string="Special Instruction")
    footer = fields.Char(string="Footer")

    # Cargo Info
    cargo_info_ids = fields.One2many(
        "freight.sea.quotation.cargo.info",
        "quotation_id",
        string="Cargo Info",
    )

    def get_report_logo_src(self):
        logo_path = get_module_resource(
            "freight_forwarding", "static", "description", "logo.png"
        )
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return "data:image/png;base64," + encoded
        return ""
