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
        "effective_date",
        "container_type",
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
