import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """18.0.1.9: Migrate freight.airline → res.partner extension.

    1. Ensure Airline res.partner.category exists with freight_role_code='airline'.
    2. For each freight.airline record:
       - Tag its partner_id as Airline.
       - Copy airline-specific fields (excl. awb_prefix) to new res.partner fields.
    3. Drop awb_prefix column from freight_air_hawb if still present.
    4. Clean up freight.airline ORM metadata (ir.model, ir.model.fields, etc.).
    5. Drop freight_airline table.
    """
    if not _table_exists(cr, 'freight_airline'):
        _logger.info("freight_airline table not found — migration skipped.")
        _cleanup_orm_metadata(cr)
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Ensure Airline category via ORM (avoids jsonb name column issues)
    category = env['res.partner.category'].search(
        [('freight_role_code', '=', 'airline')], limit=1
    )
    if not category:
        category = env['res.partner.category'].create({
            'name': 'Airline',
            'freight_role_code': 'airline',
            'is_freight_role': True,
        })
        _logger.info("Created Airline partner category id=%s", category.id)
    airline_cat_id = category.id

    # 2. Read all freight.airline records via raw SQL
    # Build SELECT defensively — table may be partially migrated from a prior run
    all_cols = [
        'id', 'partner_id', 'code', 'airline_identifier', 'iata_code',
        'commission_percentage', 'terminal', 'neutral_awb',
        'column_offset', 'row_offset', 'ccn',
        'left_margin', 'top_margin', 'analysis_code',
    ]
    select_clause = ', '.join(
        c if _column_exists(cr, 'freight_airline', c) else f'NULL AS {c}'
        for c in all_cols
    )
    cr.execute(f"SELECT {select_clause} FROM freight_airline WHERE partner_id IS NOT NULL")
    rows = cr.fetchall()
    _logger.info("Migrating %s freight.airline records to res.partner", len(rows))

    for (airline_id, partner_id, code, identifier, iata,
         commission, terminal, neutral_awb,
         col_offset, row_offset, ccn,
         left_margin, top_margin, analysis_code) in rows:

        # Tag partner as Airline (skip if already tagged)
        cr.execute(
            """
            INSERT INTO res_partner_res_partner_category_rel (partner_id, category_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (partner_id, airline_cat_id),
        )

        # Copy fields to res.partner (guard: only if column already created by ORM)
        field_map = [
            ('airline_code', code),
            ('airline_identifier', identifier),
            ('airline_iata_code', iata),
            ('airline_commission_percentage', commission),
            ('airline_terminal', terminal),
            ('airline_neutral_awb', neutral_awb),
            ('airline_column_offset', col_offset),
            ('airline_row_offset', row_offset),
            ('airline_ccn', ccn),
            ('airline_left_margin', left_margin),
            ('airline_top_margin', top_margin),
            ('airline_analysis_code', analysis_code),
        ]
        updates = [(col, val) for col, val in field_map
                   if _column_exists(cr, 'res_partner', col)]

        if updates:
            set_clause = ', '.join(f"{col} = %s" for col, _ in updates)
            params = [val for _, val in updates] + [partner_id]
            cr.execute(
                f"UPDATE res_partner SET {set_clause} WHERE id = %s",
                params,
            )

        _logger.info(
            "Migrated freight.airline #%s → res.partner #%s (code=%s)",
            airline_id, partner_id, code,
        )

    # Log orphan records (partner_id IS NULL — should not exist after 18.0.1.5)
    cr.execute("SELECT id FROM freight_airline WHERE partner_id IS NULL")
    orphans = [r[0] for r in cr.fetchall()]
    if orphans:
        _logger.warning(
            "freight.airline records with NULL partner_id (not migrated): %s", orphans
        )

    # 3. Drop awb_prefix from freight_air_hawb if still present
    if _column_exists(cr, 'freight_air_hawb', 'awb_prefix'):
        cr.execute("ALTER TABLE freight_air_hawb DROP COLUMN awb_prefix")
        _logger.info("Dropped awb_prefix column from freight_air_hawb")

    # 4 & 5. Clean ORM metadata and drop table
    _cleanup_orm_metadata(cr)
    cr.execute("DROP TABLE IF EXISTS freight_airline CASCADE")
    _logger.info("freight_airline table dropped.")


def _cleanup_orm_metadata(cr):
    cr.execute("SELECT id FROM ir_model WHERE model = 'freight.airline'")
    row = cr.fetchone()
    if not row:
        return
    model_id = row[0]
    cr.execute("DELETE FROM ir_model_access WHERE model_id = %s", (model_id,))
    cr.execute("DELETE FROM ir_rule WHERE model_id = %s", (model_id,))
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id IN "
        "(SELECT id FROM ir_model_fields WHERE model_id = %s)", (model_id,)
    )
    cr.execute("DELETE FROM ir_model_fields WHERE model_id = %s", (model_id,))
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id = %s", (model_id,)
    )
    cr.execute("DELETE FROM ir_model WHERE id = %s", (model_id,))
    _logger.info("Cleaned up ir.model metadata for freight.airline")


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())
