from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SeaQuotationItemsLine(models.Model):
    _name = "freight.sea.quotation.items.line"
    _inherit = "freight.sea.items.line.mixin"
    _description = "Sea Freight Quotation Items Line"
    _rec_name = "quotation_cargo_info_id"

    quotation_cargo_info_id = fields.Many2one(
        "freight.sea.quotation.cargo.info",
        string="Quotation Cargo Info",
        ondelete="cascade",
        required=True,
    )

    def default_get(self, fields_list):
        """Auto-set quotation_cargo_info_id from context when creating new items"""
        result = super().default_get(fields_list)
        if 'quotation_cargo_info_id' in fields_list:
            # Try to get parent cargo_info from context
            parent_id = self.env.context.get('default_quotation_cargo_info_id')
            if parent_id:
                result['quotation_cargo_info_id'] = parent_id
        return result
