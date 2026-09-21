import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Replace the stored display field with the native Product name."""
    cr.execute("""
        UPDATE product_template
        SET name = jsonb_build_object('en_US', CASE
            WHEN NULLIF(BTRIM(cc_item_code), '') IS NOT NULL
                 AND NULLIF(BTRIM(cc_item_description), '') IS NOT NULL
                THEN BTRIM(cc_item_code) || ' - ' || BTRIM(cc_item_description)
            WHEN NULLIF(BTRIM(cc_item_code), '') IS NOT NULL
                THEN BTRIM(cc_item_code)
            WHEN NULLIF(BTRIM(cc_item_description), '') IS NOT NULL
                THEN BTRIM(cc_item_description)
            ELSE COALESCE(name->>'en_US', '')
        END)
        WHERE is_charge_code = TRUE
    """)
    updated = cr.rowcount
    _logger.info('Updated native name for %s Charge Code products.', updated)

    cr.execute("""
        SELECT id, name, cc_item_code, cc_item_description
        FROM product_template
        WHERE is_charge_code = TRUE
        ORDER BY id
        LIMIT 5
    """)
    _logger.info('Charge Code name sample after migration: %s', cr.fetchall())

    cr.execute("""
        ALTER TABLE product_template
        DROP COLUMN IF EXISTS cc_display_name
    """)
    _logger.info('Removed legacy product_template.cc_display_name column if present.')