from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_charge_code = fields.Boolean(string="Is Charge Code", default=False, index=True)
    charge_code = fields.Char(string="Item Code", copy=False, index=True)
    charge_description = fields.Char(string="Freight Description")
    charge_unit = fields.Selection(
        selection=[
            ("20ft", "20FT Container"),
            ("40ft", "40FT Container"),
            ("45ft", "45FT Container"),
            ("total_container", "Total Container"),
            ("rev_ton_charge_weight", "Rev Ton/ Charge Weight"),
            ("rev_ton_rnd_up", "Rev Ton Rnd Up"),
            ("shipment", "Shipment"),
            ("house", "House"),
        ],
        string="Charge Unit",
    )
    charge_type = fields.Char(string="Charge Type")
    charge_currency_id = fields.Many2one("res.currency", string="Charge Currency")
    charge_effective_date = fields.Date(string="Effective Date")
    x_charge_display_name = fields.Char(
        string="Charge Display Name",
        compute="_compute_charge_display_name",
        store=True,
        readonly=True,
    )

    @api.depends("charge_code", "charge_description")
    def _compute_charge_display_name(self):
        for product in self:
            if product.charge_code and product.charge_description:
                product.x_charge_display_name = "%s - %s" % (
                    product.charge_code,
                    product.charge_description,
                )
            else:
                product.x_charge_display_name = product.charge_code or product.charge_description or ""

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if name:
            charge_code_products = self.search(
                args + [("charge_code", operator, name)],
                limit=limit,
            )
            if charge_code_products:
                result = [
                    (product.id, product.x_charge_display_name or product.display_name)
                    for product in charge_code_products
                ]
                if limit and len(result) >= limit:
                    return result
                existing_ids = charge_code_products.ids
                remaining = limit - len(result) if limit else limit
                standard_result = super().name_search(
                    name,
                    args + [("id", "not in", existing_ids)],
                    operator,
                    remaining,
                )
                return result + standard_result
        return super().name_search(name, args, operator, limit)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if name:
            charge_code_domain = args + [
                ("product_tmpl_id.charge_code", operator, name),
            ]
            charge_code_products = self.search(charge_code_domain, limit=limit)
            if charge_code_products:
                result = [(product.id, product.display_name) for product in charge_code_products]
                if limit and len(result) >= limit:
                    return result
                existing_ids = charge_code_products.ids
                remaining = limit - len(result) if limit else limit
                standard_result = super().name_search(
                    name,
                    args + [("id", "not in", existing_ids)],
                    operator,
                    remaining,
                )
                return result + standard_result
        return super().name_search(name, args, operator, limit)