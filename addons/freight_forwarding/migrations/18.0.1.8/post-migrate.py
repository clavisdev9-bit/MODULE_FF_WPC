import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """18.0.1.8: Bersihkan sisa metadata ORM freight.delivery.type.

    Model sudah tidak ada di kode — pastikan tidak ada orphan record
    di ir.model, ir.model.fields, ir.model.access, dan ir.model.data
    yang masih mereferensikan freight.delivery.type.
    """
    cr.execute("SELECT id FROM ir_model WHERE model = 'freight.delivery.type'")
    row = cr.fetchone()
    if not row:
        _logger.info("freight.delivery.type: no ir.model record found, skipping cleanup.")
        return

    model_id = row[0]
    _logger.info("freight.delivery.type: cleaning up ir.model id=%s", model_id)

    cr.execute("DELETE FROM ir_model_access WHERE model_id = %s", (model_id,))
    cr.execute("DELETE FROM ir_rule WHERE model_id = %s", (model_id,))
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id IN "
        "(SELECT id FROM ir_model_fields WHERE model_id = %s)", (model_id,)
    )
    cr.execute("DELETE FROM ir_model_fields WHERE model_id = %s", (model_id,))
    cr.execute("DELETE FROM ir_model_data WHERE model = 'ir.model' AND res_id = %s", (model_id,))
    cr.execute("DELETE FROM ir_model WHERE id = %s", (model_id,))

    # Drop tabel fisik jika masih ada (seharusnya sudah di-drop oleh ORM _unknown)
    cr.execute("DROP TABLE IF EXISTS freight_delivery_type CASCADE")

    _logger.info("freight.delivery.type: cleanup complete.")
