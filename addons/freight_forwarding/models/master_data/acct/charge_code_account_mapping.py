from odoo import api, fields, models


class FreightChargeCodeAccountMapping(models.Model):
    _name = 'freight.charge.code.account.mapping'
    _description = 'Freight Charge Code Account Mapping'

    product_tmpl_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade',
    )
    module_code = fields.Char(string='Module')
    job_type_id = fields.Many2one('freight.job.type', string='Job Type')
    sales_account_id = fields.Many2one('account.account', string='Sales Acc Code')
    sales_description = fields.Char(related='sales_account_id.name', string='Sales Description', readonly=True)
    cost_account_id = fields.Many2one('account.account', string='Cost Acc Code')
    cost_description = fields.Char(related='cost_account_id.name', string='Cost Description', readonly=True)
    advance_account_id = fields.Many2one('account.account', string='Adv Acc Code')

    @api.model
    def _resolve_account(self, product_tmpl, job_type, account_field):
        """FF-79: cari account mapping Job Type-specific milik Product/Charge
        Code, dan kembalikan `account.account` di field `account_field`
        (mis. 'sales_account_id' / 'cost_account_id'). Kembalikan recordset
        kosong kalau product/job_type tidak ada atau tidak ada mapping yang
        cocok -- caller bertanggung jawab jatuh ke native product account
        (property_account_income_id / property_account_expense_id)."""
        if not product_tmpl or not job_type:
            return self.env['account.account']
        mapping = self.search([
            ('product_tmpl_id', '=', product_tmpl.id),
            ('job_type_id', '=', job_type.id),
        ], limit=1)
        return mapping[account_field] if mapping else self.env['account.account']