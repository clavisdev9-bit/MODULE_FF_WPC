from odoo import api, fields, models

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sea_hbl_count = fields.Integer(
        string="Sea Jobsheet Count", compute="_compute_sea_hbl_count"
    )

    def _compute_sea_hbl_count(self):
        for rec in self:
            rec.sea_hbl_count = self.env["freight.sea.hbl"].search_count([("purchase_order_ids", "=", rec.id)])

    def action_view_sea_hbls(self):
        self.ensure_one()
        hbls = self.env["freight.sea.hbl"].search([("purchase_order_ids", "=", self.id)])
        return {
            "name": "Sea Jobsheet",
            "type": "ir.actions.act_window",
            "res_model": "freight.sea.hbl",
            "view_mode": "form" if len(hbls) == 1 else "list,form",
            "domain": [("id", "in", hbls.ids)],
            "res_id": hbls.id if len(hbls) == 1 else False,
            "context": dict(self.env.context, default_purchase_order_ids=[self.id]),
        }
