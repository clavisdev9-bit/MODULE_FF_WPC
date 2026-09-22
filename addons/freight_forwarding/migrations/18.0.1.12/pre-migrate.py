import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cr.fetchone() is not None


def _rename_column(cr, table, old, new):
    if _column_exists(cr, table, old) and not _column_exists(cr, table, new):
        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, old, new))
        _logger.info("Renamed column %s.%s -> %s.%s", table, old, table, new)


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,),
    )
    return cr.fetchone() is not None


def migrate(cr, version):
    """
    Migration 18.0.1.12 (FF-76 genericize transport document registry):

    freight.awb.master (Air-only naming) is renamed to the shared canonical
    model freight.transport.document (Air + Sea concept, Sea integration
    itself NOT done in this migration -- rename/generalization only).

    Physical SQL table for the registry (freight_awb_master) is
    DELIBERATELY KEPT as-is to avoid unnecessary schema churn -- only the
    logical Odoo model name changes. Consumer columns on
    freight_air_booking / freight_air_job (awb_master_id) ARE renamed to
    document_id since that field genuinely changes name/semantics.

    This must run BEFORE Odoo's registry init tries to reconcile the new
    field/model names against the database, otherwise Odoo would think
    these are brand-new columns/models and leave the old ones as orphaned
    stale data (violating "no duplicate old+new canonical fields").
    """
    if not _table_exists(cr, "freight_awb_master"):
        _logger.info(
            "Migration 18.0.1.12: freight_awb_master table does not exist "
            "(fresh install), skipping."
        )
        return

    _logger.info("Migration 18.0.1.12: genericizing freight.awb.master -> freight.transport.document")

    # 1. Reflect the model rename in ir_model / ir_model_fields / ir_model_data
    #    BEFORE Odoo's own model reflection runs, so it updates the existing
    #    rows in place instead of creating a parallel duplicate ir.model.
    cr.execute(
        "UPDATE ir_model SET model = %s WHERE model = %s",
        ("freight.transport.document", "freight.awb.master"),
    )
    cr.execute(
        "UPDATE ir_model_data SET name = %s WHERE module = %s AND name = %s AND model = %s",
        ("model_freight_transport_document", "freight_forwarding", "model_freight_awb_master", "ir.model"),
    )

    field_renames = [
        ("awb_no", "document_no"),
        ("awb_type", "transport_mode"),
        ("is_executed", "is_used"),
        ("execution_shipment_type", "shipment_type"),
        ("execution_shipper_id", "shipper_id"),
        ("execution_destination_id", "destination_id"),
        ("execution_pcs", "pcs"),
        ("execution_gross_weight", "gross_weight"),
        ("executed_booking_id", "used_air_booking_id"),
        ("executed_job_id", "used_air_job_id"),
        # Reverse One2many field rename (no DB column of its own, but
        # ir_model_fields/ir_model_data bookkeeping still needs updating).
        ("booking_ids", "air_booking_ids"),
    ]
    for old_name, new_name in field_renames:
        cr.execute(
            "UPDATE ir_model_fields SET model = %s, name = %s "
            "WHERE model = %s AND name = %s",
            ("freight.transport.document", new_name, "freight.awb.master", old_name),
        )
        cr.execute(
            "UPDATE ir_model_data SET name = %s "
            "WHERE module = %s AND name = %s AND model = %s",
            (
                "field_freight_transport_document__%s" % new_name,
                "freight_forwarding",
                "field_freight_awb_master__%s" % old_name,
                "ir.model.fields",
            ),
        )

    # Fields whose name stays the same (execute_by_id, execute_date,
    # service_level, is_available) still need their `model` column /
    # ir_model_data xmlid remapped to the new model name.
    unchanged_field_names = ["execute_by_id", "execute_date", "service_level", "is_available", "air_job_ids"]
    for name in unchanged_field_names:
        cr.execute(
            "UPDATE ir_model_fields SET model = %s WHERE model = %s AND name = %s",
            ("freight.transport.document", "freight.awb.master", name),
        )
        cr.execute(
            "UPDATE ir_model_data SET name = %s "
            "WHERE module = %s AND name = %s AND model = %s",
            (
                "field_freight_transport_document__%s" % name,
                "freight_forwarding",
                "field_freight_awb_master__%s" % name,
                "ir.model.fields",
            ),
        )

    # 2. Physical column renames on the registry table itself (table name
    #    freight_awb_master is kept -- see docstring).
    for old_col, new_col in field_renames[:-1]:  # exclude booking_ids (no own column)
        _rename_column(cr, "freight_awb_master", old_col, new_col)

    # 3. Drop the old unique constraint name; Odoo will (re)create
    #    document_no_uniq on next _auto_init pass since _sql_constraints
    #    was renamed accordingly.
    cr.execute('ALTER TABLE "freight_awb_master" DROP CONSTRAINT IF EXISTS "awb_no_uniq"')

    # 4. Consumer columns: freight_air_booking / freight_air_job
    #    awb_master_id -> document_id (field genuinely renamed, not just
    #    the registry's own bookkeeping).
    for table in ("freight_air_booking", "freight_air_job"):
        _rename_column(cr, table, "awb_master_id", "document_id")
        cr.execute(
            "UPDATE ir_model_fields SET name = %s "
            "WHERE model = %s AND name = %s",
            ("document_id", "freight.air.booking" if table == "freight_air_booking" else "freight.air.job", "awb_master_id"),
        )
        cr.execute(
            "UPDATE ir_model_data SET name = %s "
            "WHERE module = %s AND name = %s AND model = %s",
            (
                "field_%s__document_id" % table,
                "freight_forwarding",
                "field_%s__awb_master_id" % table,
                "ir.model.fields",
            ),
        )
        cr.execute(
            'ALTER TABLE "%s" DROP CONSTRAINT IF EXISTS "awb_master_id_uniq"' % table
        )

    # 5. freight.air.job.master_awb_master_id (computed+stored helper that
    #    reads the Master's document) -> master_document_id. Column is
    #    fully derived (recomputed on upgrade), but still renamed to avoid
    #    leaving an orphaned stale column with the old canonical name.
    _rename_column(cr, "freight_air_job", "master_awb_master_id", "master_document_id")
    cr.execute(
        "UPDATE ir_model_fields SET name = %s WHERE model = %s AND name = %s",
        ("master_document_id", "freight.air.job", "master_awb_master_id"),
    )
    cr.execute(
        "UPDATE ir_model_data SET name = %s "
        "WHERE module = %s AND name = %s AND model = %s",
        (
            "field_freight_air_job__master_document_id",
            "freight_forwarding",
            "field_freight_air_job__master_awb_master_id",
            "ir.model.fields",
        ),
    )

    _logger.info("Migration 18.0.1.12: genericization complete.")
