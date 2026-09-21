import logging

_logger = logging.getLogger(__name__)

_INDEX_NAME = 'product_template_cc_item_code_unique'


def migrate(cr, version):
    """Limit Charge Code item-code uniqueness to Charge Code products."""
    cr.execute(f'DROP INDEX IF EXISTS "{_INDEX_NAME}"')
    cr.execute(f'''
        CREATE UNIQUE INDEX "{_INDEX_NAME}"
        ON product_template (cc_item_code)
        WHERE is_charge_code = TRUE AND cc_item_code IS NOT NULL
    ''')
    _logger.info(
        'Recreated %s for Charge Code products only.',
        _INDEX_NAME,
    )
