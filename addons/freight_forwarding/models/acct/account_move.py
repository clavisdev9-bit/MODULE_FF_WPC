from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

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
                count = self.env["freight.sea.hbl"].search_count([
                    "|",
                    ("purchase_order_ids.invoice_ids", "in", rec.id),
                    ("sale_order_ids.invoice_ids", "in", rec.id),
                ])
            rec.sea_hbl_count = count

    def action_view_sea_hbls(self):
        self.ensure_one()
        hbls = self.sea_hbl_id
        if not hbls:
            hbls = self.env["freight.sea.hbl"].search([
                "|",
                ("purchase_order_ids.invoice_ids", "in", self.id),
                ("sale_order_ids.invoice_ids", "in", self.id),
            ])
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context),
        }

    def _get_sea_hbl_analytic_account(self):
        self.ensure_one()
        if self.sea_hbl_id and self.sea_hbl_id.analytic_account_id:
            return self.sea_hbl_id.analytic_account_id
        
        # Check from purchase order lines
        pos = self.line_ids.purchase_line_id.order_id
        for po in pos:
            if hasattr(po, "_get_sea_hbl_analytic_account"):
                acc = po._get_sea_hbl_analytic_account()
                if acc:
                    return acc
                    
        # Check from sale order lines
        sos = self.line_ids.sale_line_ids.order_id
        for so in sos:
            if hasattr(so, "_get_sea_hbl_analytic_account"):
                acc = so._get_sea_hbl_analytic_account()
                if acc:
                    return acc
                    
        if self.env.context.get("default_sea_hbl_id"):
            hbl = self.env["freight.sea.hbl"].browse(self.env.context.get("default_sea_hbl_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_sea_hbl_analytic_account(self):
        self.ensure_one()
        if self.move_id and hasattr(self.move_id, "_get_sea_hbl_analytic_account"):
            acc = self.move_id._get_sea_hbl_analytic_account()
            if acc:
                return acc
        if self.purchase_line_id and hasattr(self.purchase_line_id, "_get_sea_hbl_analytic_account"):
            acc = self.purchase_line_id._get_sea_hbl_analytic_account()
            if acc:
                return acc
        if self.sale_line_ids:
            for s_line in self.sale_line_ids:
                if hasattr(s_line, "_get_sea_hbl_analytic_account"):
                    acc = s_line._get_sea_hbl_analytic_account()
                    if acc:
                        return acc
        if self.env.context.get("default_sea_hbl_id"):
            hbl = self.env["freight.sea.hbl"].browse(self.env.context.get("default_sea_hbl_id"))
            if hbl and hbl.analytic_account_id:
                return hbl.analytic_account_id
        return False

    @api.depends("product_id", "move_id.sea_hbl_id")
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()
        for line in self:
            if not line.analytic_distribution and line.display_type not in ("line_section", "line_note"):
                analytic_account = line._get_sea_hbl_analytic_account()
                if analytic_account:
                    line.analytic_distribution = {str(analytic_account.id): 100.0}
