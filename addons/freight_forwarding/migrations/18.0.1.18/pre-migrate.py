import logging

_logger = logging.getLogger(__name__)

# FF-81 UAT fix: ff_valid_flag / ff_standard_charge_flag / ff_freight_collect
# change from Selection (Y/N) to Boolean on product.pricelist. Odoo's own
# ir.model.data cleanup crashes if the stale ir.model.fields.selection rows
# for these fields are still around when the field is no longer a Selection
# (AttributeError: 'Boolean' object has no attribute 'ondelete') -- drop them
# up front so the module reload converts the column cleanly.
_CHANGED_FIELDS = ('ff_valid_flag', 'ff_standard_charge_flag', 'ff_freight_collect')


def migrate(cr, version):
    cr.execute(
        """
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'product.pricelist' AND name = ANY(%s)
        )
        """,
        (list(_CHANGED_FIELDS),),
    )
    _logger.info(
        "Dropped stale ir_model_fields_selection rows for %s ahead of "
        "Selection -> Boolean conversion.", _CHANGED_FIELDS,
    )
