import logging

_logger = logging.getLogger(__name__)

# FF-75 (commit 6c2527b3a, "refactor Air and Sea jobs into Master-House
# hierarchy") renamed these models and their FK-holding child models, but
# shipped without a migration -- Odoo would otherwise just create brand-new
# EMPTY freight_sea_job / freight_air_job (+ children) tables next to the
# untouched legacy freight_sea_hbl / freight_air_hawb (+ children) tables,
# silently orphaning every existing Sea/Air Jobsheet record. This is the
# missing catch-up migration, added retroactively at the version FF-75
# itself bumped the manifest to (18.0.1.11).
RENAME_GROUPS = [
    ("freight.sea.hbl", "freight.sea.job", "hbl_id"),
    ("freight.air.hawb", "freight.air.job", "hawb_id"),
]


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cr.fetchone() is not None


def _rename_table(cr, old_table, new_table):
    if _table_exists(cr, old_table) and not _table_exists(cr, new_table):
        cr.execute('ALTER TABLE "%s" RENAME TO "%s"' % (old_table, new_table))
        _logger.info("Renamed table %s -> %s", old_table, new_table)


def _rename_column(cr, table, old_col, new_col):
    if _column_exists(cr, table, old_col) and not _column_exists(cr, table, new_col):
        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, old_col, new_col))
        _logger.info("Renamed column %s.%s -> %s.%s", table, old_col, table, new_col)


def migrate(cr, version):
    for old_model_root, new_model_root, old_fk_col in RENAME_GROUPS:
        cr.execute(
            "SELECT id, model FROM ir_model WHERE model = %s OR model LIKE %s",
            (old_model_root, old_model_root + ".%"),
        )
        model_rows = cr.fetchall()

        for model_id, old_model in model_rows:
            new_model = new_model_root + old_model[len(old_model_root):]
            old_table = old_model.replace(".", "_")
            new_table = new_model.replace(".", "_")

            # 1. Reflect the model rename in ir_model / ir_model_data BEFORE
            #    Odoo's own reflection runs, so it updates existing rows in
            #    place instead of creating a parallel duplicate ir.model
            #    (same pattern as migrations/18.0.1.12/pre-migrate.py).
            cr.execute("UPDATE ir_model SET model = %s WHERE id = %s", (new_model, model_id))
            cr.execute(
                "UPDATE ir_model_data SET name = %s "
                "WHERE module = %s AND model = %s AND res_id = %s",
                ("model_%s" % new_table, "freight_forwarding", "ir.model", model_id),
            )

            # 2. Reflect field renames (only the FK column genuinely renamed;
            #    every other field keeps its name, just needs `model` remapped).
            cr.execute("SELECT id, name FROM ir_model_fields WHERE model_id = %s", (model_id,))
            for field_id, field_name in cr.fetchall():
                new_field_name = "job_id" if field_name == old_fk_col else field_name
                cr.execute(
                    "UPDATE ir_model_fields SET model = %s, name = %s WHERE id = %s",
                    (new_model, new_field_name, field_id),
                )
                cr.execute(
                    "UPDATE ir_model_data SET name = %s "
                    "WHERE module = %s AND model = %s AND res_id = %s",
                    (
                        "field_%s__%s" % (new_table, new_field_name),
                        "freight_forwarding",
                        "ir.model.fields",
                        field_id,
                    ),
                )

            # 3. Physical table + FK column rename.
            _rename_table(cr, old_table, new_table)
            _rename_column(cr, new_table, old_fk_col, "job_id")

        # 4. Many2many relation tables (sale_order_ids / purchase_order_ids
        #    on the main Job model) -- not their own ir.model, just physical
        #    tables Odoo names after both related models' tables.
        old_table_root = old_model_root.replace(".", "_")
        new_table_root = new_model_root.replace(".", "_")
        for rel_suffix in ("sale_order_rel", "purchase_order_rel"):
            old_rel = "%s_%s" % (old_table_root, rel_suffix)
            new_rel = "%s_%s" % (new_table_root, rel_suffix)
            if _table_exists(cr, old_rel) and not _table_exists(cr, new_rel):
                cr.execute('ALTER TABLE "%s" RENAME TO "%s"' % (old_rel, new_rel))
                _rename_column(cr, new_rel, "%s_id" % old_table_root, "%s_id" % new_table_root)
                _logger.info("Renamed relation table %s -> %s", old_rel, new_rel)

    # 5. FF-75 removed 'consol' from freight.sea.job.container_type
    #    (see models/sea/hbl/hbl.py) -- remap legacy rows to 'lcl' (agreed
    #    business mapping) instead of leaving an invalid selection value.
    if _column_exists(cr, "freight_sea_job", "container_type"):
        cr.execute(
            "UPDATE freight_sea_job SET container_type = 'lcl' WHERE container_type = 'consol'"
        )
        _logger.info("FF-75 catch-up: remapped legacy container_type='consol' rows to 'lcl'.")
