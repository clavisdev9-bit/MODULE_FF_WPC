from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sea_hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Sea Jobsheet",
        index=True,
    )
    sea_hbl_count = fields.Integer(
        string="Sea Jobsheet Count", compute="_compute_sea_hbl_count"
    )

    def _compute_sea_hbl_count(self):
        for rec in self:
            count = 0
            if rec.sea_hbl_id:
                count = 1
            else:
                count = self.env["freight.sea.hbl"].search_count([("purchase_order_ids", "=", rec.id)])
            rec.sea_hbl_count = count

    def action_view_sea_hbls(self):
        self.ensure_one()
        hbls = self.sea_hbl_id or self.env["freight.sea.hbl"].search([("purchase_order_ids", "=", self.id)])
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context, default_purchase_order_ids=[self.id]),
        }

    def _get_sea_hbl_analytic_account(self):
        self.ensure_one()
        if self.sea_hbl_id and self.sea_hbl_id.analytic_account_id:
            return self.sea_hbl_id.analytic_account_id
        hbl = self.env["freight.sea.hbl"].search([("purchase_order_ids", "=", self.id)], limit=1)
        if hbl and hbl.analytic_account_id:
            return hbl.analytic_account_id
        if self.env.context.get("default_sea_hbl_id"):
            hbl = self.env["freight.sea.hbl"].browse(self.env.context.get("default_sea_hbl_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    air_hawb_id = fields.Many2one(
        "freight.air.hawb",
        string="Air Jobsheet",
        index=True,
    )
    air_hawb_count = fields.Integer(
        string="Air Jobsheet Count", compute="_compute_air_hawb_count"
    )

    def _compute_air_hawb_count(self):
        for rec in self:
            count = 0
            if rec.air_hawb_id:
                count = 1
            else:
                count = self.env["freight.air.hawb"].search_count([("purchase_order_ids", "=", rec.id)])
            rec.air_hawb_count = count

    def action_view_air_hawbs(self):
        self.ensure_one()
        hawbs = self.air_hawb_id or self.env["freight.air.hawb"].search([("purchase_order_ids", "=", self.id)])
        return {
            "name": "Air Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.air.hawb",
            "view_mode": "form" if len(hawbs) == 1 else "list,form",
            "domain": [("id", "in", hawbs.ids)],
            "res_id": hawbs.id if len(hawbs) == 1 else False,
            "context": dict(self.env.context, default_purchase_order_ids=[self.id]),
        }

    def _get_air_hawb_analytic_account(self):
        self.ensure_one()
        if self.air_hawb_id and self.air_hawb_id.analytic_account_id:
            return self.air_hawb_id.analytic_account_id
        hawb = self.env["freight.air.hawb"].search([("purchase_order_ids", "=", self.id)], limit=1)
        if hawb and hawb.analytic_account_id:
            return hawb.analytic_account_id
        if self.env.context.get("default_air_hawb_id"):
            hawb = self.env["freight.air.hawb"].browse(self.env.context.get("default_air_hawb_id"))
            if hawb and hawb.analytic_account_id:
                return hawb.analytic_account_id
        return False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.sea_hbl_id and rec.id not in rec.sea_hbl_id.purchase_order_ids.ids:
                rec.sea_hbl_id.purchase_order_ids = [(4, rec.id)]
            if rec.air_hawb_id and rec.id not in rec.air_hawb_id.purchase_order_ids.ids:
                rec.air_hawb_id.purchase_order_ids = [(4, rec.id)]
        return records

    def write(self, vals):
        res = super().write(vals)
        if "sea_hbl_id" in vals or "air_hawb_id" in vals:
            for rec in self:
                if rec.sea_hbl_id and rec.id not in rec.sea_hbl_id.purchase_order_ids.ids:
                    rec.sea_hbl_id.purchase_order_ids = [(4, rec.id)]
                if rec.air_hawb_id and rec.id not in rec.air_hawb_id.purchase_order_ids.ids:
                    rec.air_hawb_id.purchase_order_ids = [(4, rec.id)]
        return res

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.sea_hbl_id:
            invoice_vals["sea_hbl_id"] = self.sea_hbl_id.id
        else:
            hbl = self.env["freight.sea.hbl"].search([("purchase_order_ids", "=", self.id)], limit=1)
            if hbl:
                invoice_vals["sea_hbl_id"] = hbl.id

        if self.air_hawb_id:
            invoice_vals["air_hawb_id"] = self.air_hawb_id.id
        else:
            hawb = self.env["freight.air.hawb"].search([("purchase_order_ids", "=", self.id)], limit=1)
            if hawb:
                invoice_vals["air_hawb_id"] = hawb.id

        return invoice_vals


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_sea_hbl_analytic_account(self):
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_sea_hbl_analytic_account"):
            acc = self.order_id._get_sea_hbl_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_sea_hbl_id"):
            hbl = self.env["freight.sea.hbl"].browse(self.env.context.get("default_sea_hbl_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    def _get_air_hawb_analytic_account(self):
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_air_hawb_analytic_account"):
            acc = self.order_id._get_air_hawb_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_air_hawb_id"):
            hawb = self.env["freight.air.hawb"].browse(self.env.context.get("default_air_hawb_id"))
            if hawb and hawb.analytic_account_id:
                return hawb.analytic_account_id
        return False

    def _get_freight_analytic_account(self):
        return self._get_sea_hbl_analytic_account() or self._get_air_hawb_analytic_account()

    @api.depends("product_id", "order_id.sea_hbl_id", "order_id.air_hawb_id")
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if not line.analytic_distribution and line.display_type not in ("line_section", "line_note"):
                analytic_account = line._get_freight_analytic_account()
                if analytic_account:
                    line.analytic_distribution = {str(analytic_account.id): 100.0}

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        if not res.get("analytic_distribution"):
            analytic_account = self._get_freight_analytic_account()
            if analytic_account:
                res["analytic_distribution"] = {str(analytic_account.id): 100.0}
        return res

