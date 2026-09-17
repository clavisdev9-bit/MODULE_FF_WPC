import logging

from psycopg2 import sql


_logger = logging.getLogger(__name__)

CHARGE_UNIT_MAP = {
    "20ft": "20ft",
    "20FT": "20ft",
    "20 FT": "20ft",
    "40ft": "40ft",
    "40FT": "40ft",
    "40 FT": "40ft",
    "45ft": "45ft",
    "45FT": "45ft",
    "45 FT": "45ft",
    "total_container": "total_container",
    "Total Container": "total_container",
    "rev_ton_charge_weight": "rev_ton_charge_weight",
    "Rev Ton/ Charge Weight": "rev_ton_charge_weight",
    "rev_ton_rnd_up": "rev_ton_rnd_up",
    "Rev Ton Rnd Up": "rev_ton_rnd_up",
    "shipment": "shipment",
    "Shipment": "shipment",
    "house": "house",
    "House": "house",
}


def migrate(cr, version):
    if not _table_exists(cr, "freight_charge_code"):
        _logger.info("No legacy freight_charge_code table found; migration skipped.")
        return

    columns = _columns(cr, "freight_charge_code")
    required = {"id", "title"} & columns
    if required != {"id", "title"}:
        _logger.warning("Legacy charge-code table has no expected id/title columns; migration skipped.")
        return

    select_columns = ["id", "title"]
    for column in ("description", "charge_unit", "charge_type", "currency_id", "effective_date"):
        if column in columns:
            select_columns.append(column)

    cr.execute(
        sql.SQL("SELECT {} FROM freight_charge_code").format(
            sql.SQL(", ").join(map(sql.Identifier, select_columns))
        )
    )
    legacy_rows = cr.fetchall()
    for row in legacy_rows:
        values = dict(zip(select_columns, row))
        mapped_values = (
            values["title"],
            values.get("description"),
            CHARGE_UNIT_MAP.get(values.get("charge_unit")),
            values.get("charge_type"),
            values.get("currency_id"),
            values.get("effective_date"),
        )
        cr.execute(
            "SELECT id FROM product_template WHERE charge_code = %s AND is_charge_code",
            (values["title"],),
        )
        existing = cr.fetchone()
        if existing:
            product_template_id = existing[0]
            cr.execute(
                """
                UPDATE product_template
                SET name = %s, charge_description = %s, charge_unit = %s,
                    charge_type = %s, charge_currency_id = %s,
                    charge_effective_date = %s, write_uid = 1, write_date = NOW()
                WHERE id = %s
                """,
                mapped_values + (product_template_id,),
            )
        else:
            cr.execute(
                """
                INSERT INTO product_template
                    (name, charge_code, charge_description, charge_unit, charge_type,
                     charge_currency_id, charge_effective_date, is_charge_code,
                     create_uid, create_date, write_uid, write_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, true, 1, NOW(), 1, NOW())
                RETURNING id
                """,
                (values["title"], values["title"]) + mapped_values[1:],
            )
            product_template_id = cr.fetchone()[0]
            cr.execute(
                """
                INSERT INTO product_product
                    (product_tmpl_id, default_code, active, create_uid, create_date,
                     write_uid, write_date)
                VALUES (%s, %s, true, 1, NOW(), 1, NOW())
                """,
                (product_template_id, values["title"]),
            )

        cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            VALUES ('freight_forwarding', %s, 'product.template', %s, true)
            ON CONFLICT (module, name) DO NOTHING
            """,
            ("legacy_charge_code_%s" % values["id"], product_template_id),
        )

    _logger.info("Migrated %s legacy charge-code records to product.template.", len(legacy_rows))


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (table_name,))
    return cr.fetchone()[0] is not None


def _columns(cr, table_name):
    cr.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        """,
        (table_name,),
    )
    return {row[0] for row in cr.fetchall()}