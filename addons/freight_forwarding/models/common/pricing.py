"""FF-81: Charge Table (product.pricelist.item) and Cost Table
(product.supplierinfo) -- extend the native Sales Pricelist / Vendor
Pricelist models with the Freight Forwarding fields instead of building a
custom header/line model. Shared via `freight.pricing.mixin` so Air and Sea
(and Charge/Cost) never drift on field definitions or defaulting behaviour.
"""
from odoo import api, fields, models

from ..master_data.acct.charge_code import CHARGE_UNIT_SELECTION

FF_PRICING_TYPE_SELECTION = [
    ('air', 'Air'),
    ('sea', 'Sea'),
]

FF_PRICING_CARGO_SELECTION = [
    ('FCL', 'FCL'),
    ('LCL', 'LCL'),
]


class FreightPricingMixin(models.AbstractModel):
    _name = 'freight.pricing.mixin'
    _description = 'Freight Forwarding Pricing Extension (Charge/Cost Table)'

    # Not shown to the user -- only used by Air/Sea menus & actions to
    # create/filter records (see FF-81).
    ff_type = fields.Selection(FF_PRICING_TYPE_SELECTION, string='Type')
    ff_cargo = fields.Selection(FF_PRICING_CARGO_SELECTION, string='Cargo')
    ff_description = fields.Char(
        string='Description', compute='_compute_ff_description', store=True,
    )
    ff_uom_id = fields.Many2one('uom.uom', string='UoM')
    ff_vat_id = fields.Many2one('account.tax', string='VAT')
    ff_charge_unit = fields.Selection(CHARGE_UNIT_SELECTION, string='Charge Unit')

    def _ff_pricing_product_template(self):
        self.ensure_one()
        return self.product_tmpl_id or self.product_id.product_tmpl_id

    @api.depends('product_tmpl_id', 'product_id', 'product_tmpl_id.name', 'product_id.name')
    def _compute_ff_description(self):
        for rec in self:
            rec.ff_description = rec._ff_pricing_product_template().name or False

    def _apply_ff_pricing_defaults(self):
        """Default UoM/VAT/Charge Unit from the selected Charge Code, without
        overwriting a value already present (explicit override). Called from
        onchange (UI) AND create/write (server-side create/import), per
        FF-81 requirement that defaulting must not rely on onchange alone.
        """
        for rec in self:
            product = rec._ff_pricing_product_template()
            if not product:
                continue
            if not rec.ff_uom_id:
                rec.ff_uom_id = product.cc_uom_id
            if not rec.ff_vat_id:
                rec.ff_vat_id = product.cc_vat_id
            if not rec.ff_charge_unit:
                rec.ff_charge_unit = product.cc_charge_unit

    @api.onchange('product_tmpl_id', 'product_id')
    def _onchange_ff_pricing_product(self):
        self._apply_ff_pricing_defaults()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_ff_pricing_defaults()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'product_tmpl_id', 'product_id'} & set(vals):
            self._apply_ff_pricing_defaults()
        return result


class ProductPricelistItemFreight(models.Model):
    """Charge Table."""
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'freight.pricing.mixin']


class ProductSupplierinfoFreight(models.Model):
    """Cost Table."""
    _name = 'product.supplierinfo'
    _inherit = ['product.supplierinfo', 'freight.pricing.mixin']
