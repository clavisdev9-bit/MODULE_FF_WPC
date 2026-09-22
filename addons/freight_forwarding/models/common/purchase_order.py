from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sea_job_id = fields.Many2one(
        "freight.sea.job",
        string="Sea Jobsheet",
        index=True,
    )
    sea_job_count = fields.Integer(
        string="Sea Jobsheet Count", compute="_compute_sea_job_count"
    )

    def _compute_sea_job_count(self):
        for rec in self:
            count = 0
            if rec.sea_job_id:
                count = 1
            else:
                count = self.env["freight.sea.job"].search_count([("purchase_order_ids", "=", rec.id)])
            rec.sea_job_count = count

    def action_view_sea_jobs(self):
        self.ensure_one()
        hbls = self.sea_job_id or self.env["freight.sea.job"].search([("purchase_order_ids", "=", self.id)])
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.job",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context, default_purchase_order_ids=[self.id]),
        }

    def _get_sea_job_analytic_account(self):
        self.ensure_one()
        if self.sea_job_id and self.sea_job_id.analytic_account_id:
            return self.sea_job_id.analytic_account_id
        hbl = self.env["freight.sea.job"].search([("purchase_order_ids", "=", self.id)], limit=1)
        if hbl and hbl.analytic_account_id:
            return hbl.analytic_account_id
        if self.env.context.get("default_sea_job_id"):
            hbl = self.env["freight.sea.job"].browse(self.env.context.get("default_sea_job_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    air_job_id = fields.Many2one(
        "freight.air.job",
        string="Air Jobsheet",
        index=True,
    )
    air_job_count = fields.Integer(
        string="Air Jobsheet Count", compute="_compute_air_job_count"
    )

    def _compute_air_job_count(self):
        for rec in self:
            count = 0
            if rec.air_job_id:
                count = 1
            else:
                count = self.env["freight.air.job"].search_count([("purchase_order_ids", "=", rec.id)])
            rec.air_job_count = count

    def action_view_air_jobs(self):
        self.ensure_one()
        hawbs = self.air_job_id or self.env["freight.air.job"].search([("purchase_order_ids", "=", self.id)])
        return {
            "name": "Air Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.air.job",
            "view_mode": "form" if len(hawbs) == 1 else "list,form",
            "domain": [("id", "in", hawbs.ids)],
            "res_id": hawbs.id if len(hawbs) == 1 else False,
            "context": dict(self.env.context, default_purchase_order_ids=[self.id]),
        }

    def _get_air_job_analytic_account(self):
        self.ensure_one()
        if self.air_job_id and self.air_job_id.analytic_account_id:
            return self.air_job_id.analytic_account_id
        hawb = self.env["freight.air.job"].search([("purchase_order_ids", "=", self.id)], limit=1)
        if hawb and hawb.analytic_account_id:
            return hawb.analytic_account_id
        if self.env.context.get("default_air_job_id"):
            hawb = self.env["freight.air.job"].browse(self.env.context.get("default_air_job_id"))
            if hawb and hawb.analytic_account_id:
                return hawb.analytic_account_id
        return False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.sea_job_id and rec.id not in rec.sea_job_id.purchase_order_ids.ids:
                rec.sea_job_id.purchase_order_ids = [(4, rec.id)]
            if rec.air_job_id and rec.id not in rec.air_job_id.purchase_order_ids.ids:
                rec.air_job_id.purchase_order_ids = [(4, rec.id)]
        return records

    def write(self, vals):
        res = super().write(vals)
        if "sea_job_id" in vals or "air_job_id" in vals:
            for rec in self:
                if rec.sea_job_id and rec.id not in rec.sea_job_id.purchase_order_ids.ids:
                    rec.sea_job_id.purchase_order_ids = [(4, rec.id)]
                if rec.air_job_id and rec.id not in rec.air_job_id.purchase_order_ids.ids:
                    rec.air_job_id.purchase_order_ids = [(4, rec.id)]
        return res

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.sea_job_id:
            invoice_vals["sea_job_id"] = self.sea_job_id.id
        else:
            hbl = self.env["freight.sea.job"].search([("purchase_order_ids", "=", self.id)], limit=1)
            if hbl:
                invoice_vals["sea_job_id"] = hbl.id

        if self.air_job_id:
            invoice_vals["air_job_id"] = self.air_job_id.id
        else:
            hawb = self.env["freight.air.job"].search([("purchase_order_ids", "=", self.id)], limit=1)
            if hawb:
                invoice_vals["air_job_id"] = hawb.id

        return invoice_vals

    def _get_freight_job_type(self):
        """FF-79: Job Type dari Sea/Air Jobsheet terkait PO ini, dipakai
        resolve Cost Account mapping (Product/Charge Code x Job Type)."""
        self.ensure_one()
        job = self.sea_job_id or self.env["freight.sea.job"].search(
            [("purchase_order_ids", "=", self.id)], limit=1
        )
        if not job:
            job = self.air_job_id or self.env["freight.air.job"].search(
                [("purchase_order_ids", "=", self.id)], limit=1
            )
        return job.job_type_id if job else self.env["freight.job.type"]


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_sea_job_analytic_account(self):
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_sea_job_analytic_account"):
            acc = self.order_id._get_sea_job_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_sea_job_id"):
            hbl = self.env["freight.sea.job"].browse(self.env.context.get("default_sea_job_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    def _get_air_job_analytic_account(self):
        self.ensure_one()
        if self.order_id and hasattr(self.order_id, "_get_air_job_analytic_account"):
            acc = self.order_id._get_air_job_analytic_account()
            if acc:
                return acc
        if self.env.context.get("default_air_job_id"):
            hawb = self.env["freight.air.job"].browse(self.env.context.get("default_air_job_id"))
            if hawb and hawb.analytic_account_id:
                return hawb.analytic_account_id
        return False

    def _get_freight_analytic_account(self):
        return self._get_sea_job_analytic_account() or self._get_air_job_analytic_account()

    def _get_freight_job_type(self):
        """FF-79: Job Type dari Jobsheet terkait PO ini, dipakai resolve
        Cost Account mapping (Product/Charge Code x Job Type)."""
        if self.order_id and hasattr(self.order_id, "_get_freight_job_type"):
            return self.order_id._get_freight_job_type()
        return self.env["freight.job.type"]

    @api.depends("product_id", "order_id.sea_job_id", "order_id.air_job_id")
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
        if self.product_id and self.product_id.product_tmpl_id:
            job_type = self._get_freight_job_type()
            if job_type:
                cost_account = self.env["freight.charge.code.account.mapping"]._resolve_account(
                    self.product_id.product_tmpl_id, job_type, "cost_account_id"
                )
                if cost_account:
                    res["account_id"] = cost_account.id
        return res

