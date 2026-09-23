"""FF-81: Charge Table (product.pricelist header + product.pricelist.item
rules) and Cost Table (product.supplierinfo, flat) -- extend the native
Sales Pricelist / Vendor Pricelist models with the Freight Forwarding
fields instead of building a custom header/line model.

Architecture:
- Charge Table = native `product.pricelist` header (carries `ff_type`,
  hidden, used only for Air/Sea action domain/context) with native
  `product.pricelist.item` rules (carry the FF pricing fields).
- Cost Table = native flat `product.supplierinfo`, one record per
  vendor/product; NOT symmetrical with Charge Table, so it carries both
  `ff_type` and the FF pricing fields on the same (flat) record.

`freight.pricing.mixin` only holds what both `product.pricelist.item` and
`product.supplierinfo` share: the FF pricing fields and their defaulting
behaviour from the selected Charge Code (product.template).
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

# FF fields whose default comes from the Charge Code (product.template) and
# that must be refreshed whenever the Product changes, unless the caller
# explicitly supplied a value for that field in the same create/write call.
_FF_PRODUCT_SOURCE_FIELD = {
    'ff_uom_id': 'cc_uom_id',
    'ff_vat_id': 'cc_vat_id',
    'ff_charge_unit': 'cc_charge_unit',
}


class FreightPricingMixin(models.AbstractModel):
    _name = 'freight.pricing.mixin'
    _description = 'Freight Forwarding Pricing Extension (Charge/Cost Table)'

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

    @api.depends(
        'product_tmpl_id', 'product_id',
        'product_tmpl_id.cc_item_description', 'product_id.product_tmpl_id.cc_item_description',
    )
    def _compute_ff_description(self):
        for rec in self:
            product = rec._ff_pricing_product_template()
            rec.ff_description = product.cc_item_description if product else False

    def _apply_ff_pricing_defaults(self, explicit_fields=()):
        """Default UoM/VAT/Charge Unit from the selected Charge Code.

        Every FF default field NOT in `explicit_fields` is (re)filled from
        the current Product, overwriting any stale value left over from a
        previously selected Product -- selecting/changing Product always
        refreshes these, the user may still override them afterwards.
        `explicit_fields` are the FF fields the caller explicitly supplied
        in the current create/write call, and are therefore left untouched.
        """
        for rec in self:
            product = rec._ff_pricing_product_template()
            if not product:
                continue
            for field_name, source_field in _FF_PRODUCT_SOURCE_FIELD.items():
                if field_name in explicit_fields:
                    continue
                rec[field_name] = product[source_field]

    @api.onchange('product_tmpl_id', 'product_id')
    def _onchange_ff_pricing_product(self):
        self._apply_ff_pricing_defaults()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list):
            explicit_fields = {f for f in _FF_PRODUCT_SOURCE_FIELD if f in vals}
            rec._apply_ff_pricing_defaults(explicit_fields=explicit_fields)
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'product_tmpl_id', 'product_id'} & set(vals):
            explicit_fields = {f for f in _FF_PRODUCT_SOURCE_FIELD if f in vals}
            self._apply_ff_pricing_defaults(explicit_fields=explicit_fields)
        return result


class ProductPricelistItemFreight(models.Model):
    """Charge Table rule."""
    _name = 'product.pricelist.item'
    _inherit = ['product.pricelist.item', 'freight.pricing.mixin']


class ProductSupplierinfoFreight(models.Model):
    """Cost Table (flat -- not symmetrical with Charge Table)."""
    _name = 'product.supplierinfo'
    _inherit = ['product.supplierinfo', 'freight.pricing.mixin']

    # Not shown to the user -- only used by Air/Sea menus & actions to
    # create/filter records (see FF-81). Cost Table is flat, so the type
    # lives directly on the record (unlike Charge Table, where it lives on
    # the product.pricelist header -- see ProductPricelistFreight below).
    ff_type = fields.Selection(FF_PRICING_TYPE_SELECTION, string='Type')


class ProductPricelistFreight(models.Model):
    """Charge Table header."""
    _name = 'product.pricelist'
    _inherit = ['product.pricelist']

    # Not shown to the user -- only used by Air/Sea menus & actions to
    # create/filter Charge Tables (see FF-81).
    ff_type = fields.Selection(FF_PRICING_TYPE_SELECTION, string='Type')
