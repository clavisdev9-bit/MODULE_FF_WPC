from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        (mis. 'sales_account_id' / 'cost_account_id').

        - 0 mapping: recordset kosong -- caller bertanggung jawab jatuh ke
          native product account (property_account_income_id /
          property_account_expense_id).
        - 1 mapping: account dari mapping tersebut.
        - >1 mapping: TIDAK PERNAH menebak/ambil salah satu (tidak ada
          `limit=1`) -- raise UserError yang jelas, master data yang harus
          diperbaiki (dedup/hapus mapping duplikat), bukan resolver yang
          diam-diam memilih berdasarkan urutan record."""
        if not product_tmpl or not job_type:
            return self.env['account.account']
        mappings = self.search([
            ('product_tmpl_id', '=', product_tmpl.id),
            ('job_type_id', '=', job_type.id),
        ])
        if len(mappings) > 1:
            raise UserError(_(
                "Account mapping untuk Product '%(product)s' dan Job Type "
                "'%(job_type)s' ambigu -- ditemukan %(count)s baris mapping "
                "yang cocok. Perbaiki master data Module/Job Type Account "
                "Mapping produk ini supaya hanya ada satu baris per "
                "kombinasi Product + Job Type."
            ) % {
                'product': product_tmpl.display_name,
                'job_type': job_type.display_name,
                'count': len(mappings),
            })
        return mappings[account_field] if mappings else self.env['account.account']