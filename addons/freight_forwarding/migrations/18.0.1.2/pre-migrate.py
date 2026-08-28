import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.2 (FF-57):
    Reset noupdate flag on ir_model_data for freight_forwarding UOM categories and units
    so that Odoo automatically synchronizes all names to Title Case / Capitalized format on upgrade.
    """
    _logger.info("Migration 18.0.1.2: resetting noupdate on freight_forwarding UOM records...")
    cr.execute("""
        UPDATE ir_model_data
        SET noupdate = false
        WHERE module = 'freight_forwarding'
          AND (name LIKE 'uom_category_%' OR name LIKE 'uom_%');
    """)
    _logger.info("Migration 18.0.1.2: noupdate flag reset successfully.")
