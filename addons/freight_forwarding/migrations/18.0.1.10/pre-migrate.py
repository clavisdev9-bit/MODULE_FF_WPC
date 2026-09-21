import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Drop FK lama (apapun target-nya) agar Odoo bebas rebuild ke account_incoterms
    cr.execute("""
        ALTER TABLE sale_order
        DROP CONSTRAINT IF EXISTS sale_order_delivery_type_id_fkey
    """)
    _logger.info("Dropped sale_order_delivery_type_id_fkey constraint")

    # NULL-kan delivery_type_id yang tidak ada di account_incoterms
    cr.execute("""
        UPDATE sale_order
        SET delivery_type_id = NULL
        WHERE delivery_type_id IS NOT NULL
          AND delivery_type_id NOT IN (SELECT id FROM account_incoterms)
    """)
    _logger.info("Nulled %d orphan delivery_type_id values in sale_order", cr.rowcount)

    # Bersihkan ir.model metadata freight.delivery.type agar tidak di-recreate
    cr.execute("""
        DELETE FROM ir_model_fields
        WHERE model_id IN (SELECT id FROM ir_model WHERE model = 'freight.delivery.type')
    """)
    cr.execute("""
        DELETE FROM ir_model WHERE model = 'freight.delivery.type'
    """)
    _logger.info("Cleaned up ir.model metadata for freight.delivery.type")

    # Disable view inherit orphan freight.air.hawb.form.import (id=1946)
    # View ini referensi field-field yang tidak ada di model freight.air.hawb
    # dan tidak punya xmlid sehingga tidak bisa di-update via file XML
    cr.execute("""
        UPDATE ir_ui_view
        SET active = FALSE
        WHERE model = 'freight.air.hawb'
          AND name = 'freight.air.hawb.form.import'
          AND key IS NULL
    """)
    _logger.info("Disabled orphan inherit view freight.air.hawb.form.import: %d rows", cr.rowcount)
