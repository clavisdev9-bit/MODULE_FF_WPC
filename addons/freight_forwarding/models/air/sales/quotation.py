from odoo import fields, models


class AirQuotation(models.Model):
    _name = "freight.air.quotation"
    _inherit = ["sale.order", "freight.quotation"]
    _description = "Air Quotation"
    _rec_name = "name"

    # Nama tabel DB untuk _sync_sale_order_rows() di mixin
    _quotation_table = "freight_air_quotation"

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
        "valid_from",
        "container_type",
        "terms_and_conditions",
    )

    # =========================================================
    # Air-specific Fields
    # =========================================================

    # Container Type (sama seperti sea, di-sync ke sale_order)
    container_type = fields.Selection(
        selection=[
            ("fcl", "FCL"),
            ("lcl", "LCL"),
            ("consol", "Consol"),
        ],
        string="Container Type",
        required=True,
    )

    transportation_method = fields.Selection(
        selection=[
            ("air", "Air"),
            ("ocean", "Ocean"),
            ("domestic", "Domestic Ground Transportation"),
        ],
        string="Transportation Method",
    )
    expiry_date = fields.Date(string="Expiry Date")
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

    fumigation = fields.Char(string="Fumigation")
    port_of_loading_id = fields.Many2one("freight.port", string="Port Of Loading")
    port_of_discharge_id = fields.Many2one("freight.port", string="Port Of Discharge")
    via_port_id = fields.Many2one("freight.port", string="Via Port")
    via2_id = fields.Many2one("freight.port", string="Via2")
    via3_id = fields.Many2one("freight.port", string="Via3")
    shipping_line_id = fields.Many2one("freight.carrier", string="Shipping Line")

    # Relasi many2many — nama tabel relasi air-specific
    transaction_ids = fields.Many2many(
        "payment.transaction",
        "freight_air_quotation_transaction_rel",
        "air_quotation_id",
        "transaction_id",
        string="Transactions",
        copy=False,
    )
    tag_ids = fields.Many2many(
        "crm.tag",
        "freight_air_quotation_tag_rel",
        "air_quotation_id",
        "tag_id",
        string="Tags",
    )

    # Cargo Info (air-specific comodel)
    cargo_info_ids = fields.One2many(
        "freight.air.quotation.cargo.info",
        "quotation_id",
        string="Cargo Info",
    )

    # Shipment Info — Air-specific (airport / airline) — TODO: akan ditambahkan nanti


class SaleOrderAirCompat(models.Model):
    _inherit = "sale.order"

    def write(self, vals):
        res = super().write(vals)
        # Reverse sync: jika SO diupdate dari native Odoo (misal klik Cancel di Sales app),
        # sync kembali kolom yang berubah ke custom quotation tables (air)
        # Raw SQL digunakan agar tidak mentrigger write loop.
        
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
