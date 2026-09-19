from odoo import api, fields, models

class SeaBookingConvertWizard(models.TransientModel):
    _name = "freight.sea.booking.convert.wizard"
    _description = "Convert Sea Quotation to Sea Booking"

    quotation_id = fields.Many2one(
        "sale.order",
        string="Quotation",
        readonly=True,
    )

    # Auto-filled from quotation
    customer_id = fields.Many2one("res.partner", string="Customer Name")
    delivery_type_id = fields.Many2one("account.incoterms", string="Delivery Type")
    origin_port_id = fields.Many2one("freight.port", string="Origin Port (POL)")
    destination_port_id = fields.Many2one("freight.port", string="Destination Port (POD)")
    destination_country_id = fields.Many2one("res.country", string="Destination Country")
    origin_country_id = fields.Many2one("res.country", string="Cargo Origin Country")
    salesman_id = fields.Many2one("hr.employee", string="Salesman")
    payment_term_id = fields.Many2one("account.payment.term", string="Terms Payment")

    freight_type = fields.Selection(
        selection=[
            ("import", "Import"),
            ("export", "Export"),
        ],
        string="Type",
    )
    vessel_id = fields.Many2one(
        "freight.vessel",
        string="Vessel Name",
    )
    voyage_no = fields.Char(string="Voyage No.")
    etd = fields.Date(string="ETD (Departure)")
    eta = fields.Date(string="ETA (Arrival)")

    # Optional
    bl_no = fields.Char(string="B/L No.")
    customer_code = fields.Char(string="Booking Customer Code")
    import_job_no = fields.Char(string="Import Job Number")
    nomination_cargo = fields.Boolean(string="Nomination Cargo")
    railing = fields.Boolean(string="Railing")

    def _get_destination_country(self, quotation):
        return quotation.delivery_country_id or quotation.delivery_city.country_id

    def _get_origin_country(self, quotation):
        return quotation.pickup_country_id or quotation.pickup_city.country_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        quotation_id = self.env.context.get("active_id")
        if quotation_id:
            quotation = self.env["sale.order"].browse(quotation_id)
            destination_country = self._get_destination_country(quotation)
            origin_country = self._get_origin_country(quotation)
            res.update(
                {
                    "quotation_id": quotation_id,
                    "freight_type": quotation.freight_type,
                    "customer_id": quotation.partner_id.id,
                    "delivery_type_id": quotation.delivery_type_id.id,
                    "salesman_id": quotation.salesman_id.id,
                    "payment_term_id": quotation.payment_term_id.id,
                }
            )
        return res

    def action_convert_to_booking(self):
        """Convert quotation to sea booking."""
        self.ensure_one()

        quotation = self.quotation_id
        
        # Ambil semua variant quotation yang bersangkutan
        original_id = quotation.original_quotation_id.id if quotation.original_quotation_id else quotation.id
        domain = ['|', ('id', '=', original_id), ('original_quotation_id', '=', original_id)]
        all_variants = self.env["sale.order"].search(domain)

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
                "sale_order_ids": [(6, 0, all_variants.ids)],
                "partner_id": self.customer_id.id,
                "delivery_type_id": self.delivery_type_id.id,
                "destination_country_id": destination_country.id if destination_country else False,
                "origin_country_id": origin_country.id if origin_country else False,
                "from_city": quotation.pickup_city.id,
                "to_city": quotation.delivery_city.id,
                "salesman_id": self.salesman_id.id,
                "payment_term_id": self.payment_term_id.id,
                "ship_mode": quotation.sea_ship_mode,
                "commodity_id": quotation.commodity_id.id,
                "service_level": quotation.service_level,
                "freight_type": self.freight_type,
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
                "company_id": quotation.company_id.id,
            }
        )

        # Return action to open created booking
        return {
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.booking",
            "res_id": booking.id,
            "view_mode": "form",
            "target": "current",
        }
