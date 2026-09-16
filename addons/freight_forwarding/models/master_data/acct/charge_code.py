from odoo import fields, models


class FreightChargeCode(models.Model):
    _name = 'freight.charge.code'
    _description = 'Freight Charge Code'
    _rec_name = 'item_code'

    _sql_constraints = [
        ('item_code_unique', 'UNIQUE(item_code)', 'Item Code must be unique!')
    ]

    # -------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------
    item_code = fields.Char(string='Item Code', required=True, size=30)
    item_description = fields.Char(string='Item Description')
    local_name = fields.Char(string='Local Name')
    item_short_code = fields.Char(string='Item Short Code')
    charge_type = fields.Selection([
        ('F', 'FREIGHT'),
        ('H', 'HANDLING'),
        ('O', 'OTHER'),
        ('P', 'PERMIT'),
        ('S', 'STORAGE'),
        ('T', 'TRUCKING'),
    ], string='Charge Type')

    # -------------------------------------------------------------
    # Scope / Behaviour
    # -------------------------------------------------------------
    module_code = fields.Char(string='Module')
    department_code = fields.Char(string='Department Code')
    recoverable = fields.Boolean(string='Recoverable')
    split_by_method = fields.Selection([
        ('J', 'Job'),
        ('C', 'Charge Weight'),
        ('V', 'Volume'),
        ('W', 'Gross Weight'),
    ], string='Split By Method')
    charge_unit = fields.Char(string='Charge Unit')
    uom_id = fields.Many2one('uom.uom', string='Unit Of Measurement')
    site_code = fields.Char(string='Site Code')

    # -------------------------------------------------------------
    # Accounting
    # -------------------------------------------------------------
    sales_account_id = fields.Many2one('account.account', string='Sales Account')
    cost_account_id = fields.Many2one('account.account', string='Cost Account')
    sales_provision_account_id = fields.Many2one('account.account', string='Sales Provision Account')
    provision_account_id = fields.Many2one('account.account', string='Provision Account')
    cost_center_code = fields.Char(string='Cost Center Code')
    sales_analysis_code = fields.Char(string='Sales Analysis Code')
    cost_analysis_code = fields.Char(string='Cost Analysis Code')

    # -------------------------------------------------------------
    # Tax / Currency
    # -------------------------------------------------------------
    billing_currency_id = fields.Many2one('res.currency', string='Billing Curr Code')
    vat_id = fields.Many2one('account.tax', string='Code')
    cost_vat_id = fields.Many2one('account.tax', string='Cost Code')
    wht_tax_id = fields.Many2one('account.tax', string='WHT Code')

    # -------------------------------------------------------------
    # Other Configuration
    # -------------------------------------------------------------
    consolidation_item_id = fields.Many2one(
        "freight.charge.code", string="Consolidation Item Code"
    )
    locked = fields.Boolean(string='Lock')
    sales_cost_type = fields.Selection([
        ('S', 'Sales'),
        ('C', 'Cost'),
    ], string='Sales/Cost')
    cost_amount = fields.Float(string='Cost', digits=(11, 2))
    cost_percent = fields.Float(string='Cost Percent', digits=(11, 2))

    active = fields.Boolean(string='Active', default=True)

    account_mapping_ids = fields.One2many(
        'freight.charge.code.account.mapping', 'charge_code_id',
        string='Module / Job Type Account Mapping',
    )
