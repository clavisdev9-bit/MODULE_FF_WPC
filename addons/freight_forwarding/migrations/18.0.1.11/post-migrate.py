import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """18.0.1.11 post-migrate:
    1. Backfill name for all is_charge_code products.
    2. Add UNIQUE constraint on cc_item_code (non-null).
    3. Quantitative verification log.
    """
    # 1. Backfill the native product name
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
    _logger.info("Backfilled product name for %s charge code products.", cr.rowcount)

    # 2. Unique constraint on cc_item_code (partial: only where not null)
    cr.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'product_template'
                AND indexname = 'product_template_cc_item_code_unique'
            ) THEN
                CREATE UNIQUE INDEX product_template_cc_item_code_unique
                ON product_template (cc_item_code)
                WHERE cc_item_code IS NOT NULL;
            END IF;
        END$$;
    """)
    _logger.info("Ensured UNIQUE index on product_template.cc_item_code.")

    # 3. Verification
    cr.execute("SELECT COUNT(*) FROM product_template WHERE is_charge_code = TRUE")
    total_products = cr.fetchone()[0]

    cr.execute("""
        SELECT COUNT(*) FROM product_template
        WHERE is_charge_code = TRUE AND name IS NOT NULL
    """)
    with_name = cr.fetchone()[0]

    cr.execute("""
        SELECT COUNT(*) FROM product_template
        WHERE is_charge_code = TRUE AND cc_charge_unit IS NULL
        AND cc_item_code IS NOT NULL
    """)
    null_units = cr.fetchone()[0]

    _logger.info(
        "18.0.1.11 verification: total charge code products=%s, "
        "with product name=%s, null cc_charge_unit=%s",
        total_products, with_name, null_units,
    )
    if null_units:
        cr.execute("""
            SELECT id, cc_item_code FROM product_template
            WHERE is_charge_code = TRUE AND cc_charge_unit IS NULL
            AND cc_item_code IS NOT NULL
        """)
        _logger.warning(
            "Products with NULL cc_charge_unit (review manual): %s",
            cr.fetchall(),
        )
