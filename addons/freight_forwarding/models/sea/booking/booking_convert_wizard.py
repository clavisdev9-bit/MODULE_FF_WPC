from odoo import api, fields, models

class SeaBookingConvertWizard(models.TransientModel):
    _name = "freight.sea.booking.convert.wizard"
    _description = "Convert Sea Quotation to Sea Booking"

    quotation_id = fields.Many2one(
        "freight.sea.quotation",
        string="Quotation",
        readonly=True,
    )

    # Auto-filled from quotation
    customer_id = fields.Many2one("res.partner", string="Customer Name")
    delivery_type_id = fields.Many2one("freight.delivery.type", string="Delivery Type")
    currency_id = fields.Many2one("res.currency", string="Currency")
    origin_port_id = fields.Many2one("freight.port", string="Origin Port (POL)")
    destination_port_id = fields.Many2one("freight.port", string="Destination Port (POD)")
    destination_country_id = fields.Many2one("res.country", string="Destination Country")
    origin_country_id = fields.Many2one("res.country", string="Cargo Origin Country")
    contact_person = fields.Char(string="Contact Person")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    salesman_id = fields.Many2one("res.partner", string="Salesman")
    payment_term_id = fields.Many2one("account.payment.term", string="Terms Payment")

    # Require user input
    type = fields.Selection(
        selection=[
            ("Import", "Import"),
            ("Export", "Export"),
        ],
        string="Type",
        required=True,
    )
    vessel_id = fields.Many2one(
        "freight.vessel",
        string="Vessel Name",
        required=True,
    )
    voyage_no = fields.Char(string="Voyage No.", required=True)
    etd = fields.Date(string="ETD (Departure)")
    eta = fields.Date(string="ETA (Arrival)")

    # Optional
    bl_no = fields.Char(string="B/L No.")
    customer_code = fields.Char(string="Booking Customer Code")
    import_job_no = fields.Char(string="Import Job Number")
    nomination_cargo = fields.Boolean(string="Nomination Cargo")
    railing = fields.Boolean(string="Railing")

    def _get_destination_country(self, quotation):
        return quotation.destination_country_id or quotation.destination_id.country_id

    def _get_origin_country(self, quotation):
        return quotation.source_country_id or quotation.origin_id.country_id

    def _prepare_booking_cargo_info_vals(self, cargo_info, booking):
        return {
            "booking_id": booking.id,
            "uom": cargo_info.uom,
            "package_type": cargo_info.package_type.id,
            "container_no": cargo_info.container_no,
            "seal_no": cargo_info.seal_no,
            "container_type_id": cargo_info.container_type_id.id,
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

    def _copy_cargo_info_to_booking(self, quotation, booking):
        booking_detail_model = self.env["freight.sea.booking.cargo.info"]

        for cargo_info in quotation.cargo_info_ids:
            booking_detail_model.create(
                self._prepare_booking_cargo_info_vals(cargo_info, booking)
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        quotation_id = self.env.context.get("active_id")
        if quotation_id:
            quotation = self.env["freight.sea.quotation"].browse(quotation_id)
            destination_country = self._get_destination_country(quotation)
            origin_country = self._get_origin_country(quotation)
            res.update(
                {
                    "quotation_id": quotation_id,
                    "customer_id": quotation.partner_id.id,
                    "delivery_type_id": quotation.delivery_type_id.id,
                    "currency_id": quotation.currency_id.id,
                    "origin_port_id": quotation.port_of_loading_id.id,
                    "destination_port_id": quotation.port_of_discharge_id.id,
                    "destination_country_id": destination_country.id if destination_country else False,
                    "origin_country_id": origin_country.id if origin_country else False,
                    "contact_person": quotation.contact_person,
                    "phone": quotation.phone,
                    "email": quotation.email,
                    "salesman_id": quotation.user_id.id,
                    "payment_term_id": quotation.payment_term_id.id,
                }
            )
        return res

    def action_convert_to_booking(self):
        """Convert quotation to sea booking."""
        self.ensure_one()

        quotation = self.quotation_id
        destination_country = self._get_destination_country(quotation)
        origin_country = self._get_origin_country(quotation)

        # Generate booking number
        booking_no = self.env["ir.sequence"].next_by_code(
            "freight.sea.booking"
        ) or fields.Date.today().strftime("WPCS%d%m-001")

        # Create sea booking
        booking = self.env["freight.sea.booking"].create(
            {
                "name": booking_no,
                "quotation_id": self.quotation_id.id,
                "customer_id": self.customer_id.id,
                "delivery_type_id": self.delivery_type_id.id,
                "origin_port_id": self.origin_port_id.id,
                "destination_port_id": self.destination_port_id.id,
                "destination_country_id": destination_country.id if destination_country else False,
                "cargo_origin_country_id": origin_country.id if origin_country else False,
                "phone": self.phone,
                "email": self.email,
                "salesman_id": self.salesman_id.id,
                "payment_term_id": self.payment_term_id.id,
                "freight_type": quotation.freight_type,
                "type": self.type,
                "vessel_id": self.vessel_id.id,
                "voyage_no": self.voyage_no,
                "etd": self.etd,
                "eta": self.eta,
                "bl_no": self.bl_no,
                "customer_reference": self.customer_code,
                "import_job_no": self.import_job_no,
                "nomination_cargo": self.nomination_cargo,
                "railing": self.railing,
                "booking_date": fields.Datetime.now(),
                "job_date": fields.Date.today(),
            }
        )

        self._copy_cargo_info_to_booking(quotation, booking)

        # Return action to open created booking
        return {
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "target": "current",
        }
