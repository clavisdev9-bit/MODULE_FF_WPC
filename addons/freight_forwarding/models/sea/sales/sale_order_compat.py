from odoo import api, fields, models


class SaleOrderCompat(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        res = super().write(vals)
        # Reverse sync: jika SO diupdate dari native Odoo (misal klik Cancel di Sales app),
        # sync kembali kolom yang berubah ke custom quotation tables (sea & air)
        # Raw SQL digunakan agar tidak mentrigger write loop.
        
        sea_model = self.env.get("freight.sea.quotation")
        if sea_model is not None:
            sea_cols = getattr(sea_model, "_SALE_ORDER_SYNC_COLUMNS", [])
            sea_update = {k: v for k, v in vals.items() if k in sea_cols}
            if sea_update:
                set_clauses = []
                params = []
                for k, v in sea_update.items():
                    set_clauses.append(f"{k} = %s")
                    params.append(v)
                params.append(self.ids)
                self.env.cr.execute(
                    f"UPDATE freight_sea_quotation SET {', '.join(set_clauses)} WHERE id = ANY(%s)",
                    params,
                )
                
        air_model = self.env.get("freight.air.quotation")
        if air_model is not None:
            air_cols = getattr(air_model, "_SALE_ORDER_SYNC_COLUMNS", [])
            air_update = {k: v for k, v in vals.items() if k in air_cols}
            if air_update:
                set_clauses = []
                params = []
                for k, v in air_update.items():
                    set_clauses.append(f"{k} = %s")
                    params.append(v)
                params.append(self.ids)
                self.env.cr.execute(
                    f"UPDATE freight_air_quotation SET {', '.join(set_clauses)} WHERE id = ANY(%s)",
                    params,
                )
                
        return res

    freight_type = fields.Selection(
        selection=[
            ("export", "Export"),
            ("import", "Import"),
        ],
        string="Quotation Type",
    )
    container_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Container Type",
    )

    transportation_method = fields.Selection(
        selection=[
            ("air", "Air"),
            ("ocean", "Ocean"),
            ("domestic", "Domestic Ground Transportation"),
        ],
        string="Transportation Method",
    )

    quotation_title = fields.Char(string="Quotation Title")
    contact_person = fields.Char(string="Contact Person")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    service_level = fields.Selection(
        [
            ("p1", "P1"),
            ("p2", "P2"),
            ("p3", "P3"),
            ("p4", "P4"),
        ],
        string="Service Level",
    )

    delivery_type_id = fields.Many2one("freight.delivery.type", string="Delivery Type")
    effective_date = fields.Date(string="Effective Date")
    expiry_date = fields.Date(string="Expiry Date")
    reference_number = fields.Char(string="Reference Number")
    commodity_id = fields.Many2one("freight.commodity", string="Commodity")

    source_street = fields.Char(string="Source Street")
    source_street2 = fields.Char(string="Source Street 2")
    source_city = fields.Char(string="Source City")
    source_state_id = fields.Many2one("res.country.state", string="Source State")
    source_zip = fields.Char(string="Source Zip")
    source_country_id = fields.Many2one("res.country", string="Source Country")

    destination_street = fields.Char(string="Destination Street")
    destination_street2 = fields.Char(string="Destination Street 2")
    destination_city = fields.Char(string="Destination City")
    destination_state_id = fields.Many2one(
        "res.country.state", string="Destination State"
    )
    destination_zip = fields.Char(string="Destination Zip")
    destination_country_id = fields.Many2one(
        "res.country", string="Destination Country"
    )

    description_of_goods = fields.Char(string="Description of Goods")
    quantity = fields.Float(string="Quantity")
    actual_weight = fields.Float(string="Actual Weight (Kg)")
    volume = fields.Float(string="Volume (Kg)")
    chargeable_weight = fields.Float(string="Chargeable Weight (Kg)")
    fumigation = fields.Char(string="Fumigation")
    has_insurance = fields.Boolean(string="Has Insurance")
    insurance_id = fields.Many2one("freight.insurance", string="Insurance")

    loose_quantity = fields.Integer(string="Loose Quantity")
    pcs = fields.Integer(string="PCS")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")
    dimension = fields.Float(string="Dimension")

    port_of_loading_id = fields.Many2one("freight.port", string="Port Of Loading")
    port_of_discharge_id = fields.Many2one("freight.port", string="Port Of Discharge")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    origin_id = fields.Many2one("freight.location", string="Origin")
    destination_id = fields.Many2one("freight.location", string="Destination")
    via2_id = fields.Many2one("freight.port", string="Via2")
    via3_id = fields.Many2one("freight.port", string="Via3")
    shipping_line_id = fields.Many2one("freight.carrier", string="Shipping Line")
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

    header = fields.Char(string="Header")
    special_instruction = fields.Text(string="Special Instruction")
    footer = fields.Char(string="Footer")