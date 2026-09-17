import logging

from psycopg2 import sql


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not _table_exists(cr, "freight_delivery_type"):
        _logger.info("No legacy freight_delivery_type table found; migration skipped.")
        return

    cr.execute("SELECT id, code, name FROM freight_delivery_type ORDER BY id")
    legacy_records = cr.fetchall()
    mappings = {}
    for legacy_id, code, name in legacy_records:
        cr.execute(
            "SELECT id FROM account_incoterms WHERE code = %s LIMIT 1",
            (code,),
        )
        row = cr.fetchone()
        if row:
            incoterm_id = row[0]
        else:
            cr.execute(
                """
                INSERT INTO account_incoterms (code, name, active, create_uid, create_date, write_uid, write_date)
                VALUES (%s, jsonb_build_object('en_US', %s), true, 1, NOW(), 1, NOW())
                RETURNING id
                """,
                (code, name),
            )
            incoterm_id = cr.fetchone()[0]
        mappings[legacy_id] = incoterm_id

    cr.execute(
        """
        SELECT con.conname, cls.relname
        FROM pg_constraint con
        JOIN pg_class cls ON cls.oid = con.conrelid
        WHERE con.contype = 'f'
          AND con.confrelid = 'freight_delivery_type'::regclass
        """
    )
    for constraint_name, table_name in cr.fetchall():
        cr.execute(
            sql.SQL("ALTER TABLE {} DROP CONSTRAINT IF EXISTS {} CASCADE").format(
                sql.Identifier(table_name), sql.Identifier(constraint_name)
            )
        )

    for column_name in ("delivery_type_id", "delivery_type"):
        cr.execute(
            """
            SELECT table_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND column_name = %s
            """,
            (column_name,),
        )
        for (table_name,) in cr.fetchall():
            if table_name == "freight_delivery_type":
                continue
            for legacy_id, incoterm_id in mappings.items():
                cr.execute(
                    sql.SQL("UPDATE {} SET {} = %s WHERE {} = %s").format(
                        sql.Identifier(table_name),
                        sql.Identifier(column_name),
                        sql.Identifier(column_name),
                    ),
                    (incoterm_id, legacy_id),
                )

    for legacy_id, incoterm_id in mappings.items():
        cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            VALUES ('freight_forwarding', %s, 'account.incoterms', %s, true)
            ON CONFLICT (module, name) DO NOTHING
            """,
            ("legacy_delivery_type_%s" % legacy_id, incoterm_id),
        )
    cr.execute(
        "DELETE FROM ir_model_access WHERE model_id IN "
        "(SELECT id FROM ir_model WHERE model = 'freight.delivery.type')"
    )
    _logger.info("Migrated %s freight.delivery.type records to account.incoterms.", len(mappings))


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (table_name,))
    return cr.fetchone()[0] is not None