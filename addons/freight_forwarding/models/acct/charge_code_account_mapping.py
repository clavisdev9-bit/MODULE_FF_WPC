from odoo import fields, models


class FreightChargeCodeAccountMapping(models.Model):
    _name = 'freight.charge.code.account.mapping'
    _description = 'Freight Charge Code Account Mapping'

    charge_code_id = fields.Many2one(
        'freight.charge.code', required=True, ondelete='cascade',
    )
    module_code = fields.Char(string='Module')
    job_type_id = fields.Many2one('freight.job.type', string='Job Type')
    sales_account_id = fields.Many2one('account.account', string='Sales Acc Code')
    sales_description = fields.Char(related='sales_account_id.name', string='Sales Description', readonly=True)
    cost_account_id = fields.Many2one('account.account', string='Cost Acc Code')
    cost_description = fields.Char(related='cost_account_id.name', string='Cost Description', readonly=True)
    advance_account_id = fields.Many2one('account.account', string='Adv Acc Code')
