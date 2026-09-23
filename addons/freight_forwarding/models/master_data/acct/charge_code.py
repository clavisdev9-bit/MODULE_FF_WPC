from odoo import api, fields, models
from odoo.osv import expression

# FF-81: shared Charge Unit definition -- reused by Charge Code
# (product.template), Charge Table (product.pricelist.item) and Cost Table
# (product.supplierinfo) so the three never drift apart. Existing keys are
# kept as-is for backward compatibility with existing Charge Code data.
CHARGE_UNIT_SELECTION = [
    ('20ft', '20FT Container'),
    ('40ft', '40FT Container'),
    ('45ft', '45FT Container'),
    ('total_container', 'Total Container'),
    ('rev_ton_cw', 'Rev Ton/ Charge Weight'),
    ('rev_ton_rnd', 'Rev Ton Rnd Up'),
    ('shipment', 'Shipment'),
    ('house', 'House'),
    ('subhouse_bl', 'Subhouse B/L'),
    ('volume', 'Volume'),
    ('weight', 'Weight'),
    ('pcs', 'Pcs'),
    ('ccfee', 'CCFEE'),
    ('block_4m3', 'Block of 4 M3'),
    ('block_3m3', 'Block of 3 M3'),
    ('invoice_charge_weight', 'Invoice Charge Weight'),
]

# FF-81: Charge Units whose Quantity formula is documented/confirmed in the
# UAT. Container-type units share the same "quantity = number of
# containers" rule. Any Charge Unit not listed here has no confirmed
# formula yet and must NOT be guessed (see FF-81 Out of Scope).
_CONTAINER_CHARGE_UNITS = ('20ft', '40ft', '45ft', 'total_container')


def compute_charge_quantity(charge_unit, container_count=None, cm3=None, kgs=None,
                             house_count=None, volume=None, weight=None, pcs=None):
    """Compute Quantity for a Charge Table / Cost Table line, based on the
    effective Charge Unit, following the formulas confirmed in FF-81 UAT.

    Returns ``None`` when `charge_unit` has no documented formula (the
    Charge Unit selection stays available for those, but their quantity
    behaviour is out of scope until a formula is confirmed).
    """
    if charge_unit in _CONTAINER_CHARGE_UNITS:
        return container_count
    if charge_unit == 'rev_ton_cw':
        if cm3 is None or kgs is None:
            return None
        return max(cm3 / 6000.0, kgs)
    if charge_unit == 'shipment':
        return 1
    if charge_unit == 'house':
        return house_count
    if charge_unit == 'volume':
        return volume
    if charge_unit == 'weight':
        return weight
    if charge_unit == 'pcs':
        return pcs
    return None


class ProductTemplateChargeCode(models.Model):
    _inherit = 'product.template'

    is_charge_code = fields.Boolean(string='Is Charge Code', default=False, index=True)

    # --- Identity ---
    cc_item_code = fields.Char(string='Item Code', size=30)
    cc_item_description = fields.Char(string='Item Description')
    cc_local_name = fields.Char(string='Local Name')
    cc_item_short_code = fields.Char(string='Item Short Code')
    cc_charge_type = fields.Selection([
        ('F', 'FREIGHT'),
        ('H', 'HANDLING'),
        ('O', 'OTHER'),
        ('P', 'PERMIT'),
        ('S', 'STORAGE'),
        ('T', 'TRUCKING'),
    ], string='Charge Type')

    # --- Scope / Behaviour ---
    cc_module_code = fields.Char(string='Module')
    cc_department_code = fields.Char(string='Department Code')
    cc_recoverable = fields.Boolean(string='Recoverable')
    cc_split_by_method = fields.Selection([
        ('J', 'Job'),
        ('C', 'Charge Weight'),
        ('V', 'Volume'),
        ('W', 'Gross Weight'),
    ], string='Split By Method')
    cc_charge_unit = fields.Selection(CHARGE_UNIT_SELECTION, string='Charge Unit')
    cc_uom_id = fields.Many2one('uom.uom', string='Unit Of Measurement')
    cc_site_code = fields.Char(string='Site Code')

    # --- Accounting ---
    cc_sales_account_id = fields.Many2one('account.account', string='Sales Account')
    cc_cost_account_id = fields.Many2one('account.account', string='Cost Account')
    cc_sales_provision_account_id = fields.Many2one('account.account', string='Sales Provision Account')
    cc_provision_account_id = fields.Many2one('account.account', string='Provision Account')
    cc_cost_center_code = fields.Char(string='Cost Center Code')
    cc_sales_analysis_code = fields.Char(string='Sales Analysis Code')
    cc_cost_analysis_code = fields.Char(string='Cost Analysis Code')

    # --- Tax / Currency ---
    cc_billing_currency_id = fields.Many2one('res.currency', string='Billing Curr Code')
    # FF-81: UI label cleanup only (Code/Cost Code/WHT Code -> VAT/Cost
    # VAT/WHT) -- technical field names are unchanged.
    cc_vat_id = fields.Many2one('account.tax', string='VAT')
    cc_cost_vat_id = fields.Many2one('account.tax', string='Cost VAT')
    cc_wht_tax_id = fields.Many2one('account.tax', string='WHT')

    # --- Other Configuration ---
    cc_consolidation_item_id = fields.Many2one(
        'product.template',
        string='Consolidation Item Code',
        domain=[('is_charge_code', '=', True)],
    )
    cc_locked = fields.Boolean(string='Lock')
    cc_sales_cost_type = fields.Selection([
        ('S', 'Sales'),
        ('C', 'Cost'),
    ], string='Sales/Cost')
    cc_cost_amount = fields.Float(string='Cost', digits=(11, 2))
    cc_cost_percent = fields.Float(string='Cost Percent', digits=(11, 2))

    # --- Account Mapping (One2many child) ---
    # NB: relasi ke model lain lewat STRING nama model
    # ('freight.charge.code.account.mapping'), TIDAK perlu
    # `from .charge_code_account_mapping import ...` di sini.
    # Itu penyebab circular import sebelumnya.
    cc_account_mapping_ids = fields.One2many(
        'freight.charge.code.account.mapping',
        'product_tmpl_id',
        string='Module / Job Type Account Mapping',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_charge_code', self.env.context.get('default_is_charge_code')):
                vals['name'] = self._charge_code_name(vals)
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if {'is_charge_code', 'cc_item_code', 'cc_item_description'} & set(vals):
            for rec in self.filtered('is_charge_code'):
                super(ProductTemplateChargeCode, rec).write({
                    'name': self._charge_code_name({
                        'cc_item_code': rec.cc_item_code,
                        'cc_item_description': rec.cc_item_description,
                    }),
                })
        return result

    @api.model
    def _charge_code_name(self, vals):
        parts = [
            part.strip()
            for part in (vals.get('cc_item_code'), vals.get('cc_item_description'))
            if part and part.strip()
        ]
        return ' - '.join(parts) or False

    @api.onchange('cc_item_code', 'cc_item_description')
    def _onchange_charge_code_name(self):
        for rec in self:
            if rec.is_charge_code:
                rec.name = self._charge_code_name({
                    'cc_item_code': rec.cc_item_code,
                    'cc_item_description': rec.cc_item_description,
                })


class ProductProductChargeCodeSearch(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        results = super().name_search(name, args=args, operator=operator, limit=limit)
        if results or not name:
            return results

        domain = expression.AND([
            args or [],
            ['|', ('cc_item_code', operator, name), ('name', operator, name)],
        ])
        products = self.search(domain, limit=limit)
        return [(product.id, product.display_name) for product in products.sudo()]