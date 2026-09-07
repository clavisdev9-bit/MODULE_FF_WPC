import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.3:
    1. Standardize service_level field as fields.Selection across all models (Sea and Air).
    2. Clean up any orphaned ir_model_fields_selection records and ir_model_data references
       to prevent AttributeError: 'Char' object has no attribute 'ondelete'.
    3. Normalize existing table data to valid selection keys ('p1', 'p2', 'p3', 'p4').
    """
    _logger.info("Migration 18.0.1.3: Standardizing service_level across all models to Selection...")

    # 1. Clean up orphaned XML IDs for service_level selections or any selection with ttype != 'selection'
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields.selection'
          AND (
              res_id IN (
                  SELECT s.id
                  FROM ir_model_fields_selection s
                  JOIN ir_model_fields f ON s.field_id = f.id
                  WHERE f.ttype != 'selection'
              )
              OR name LIKE 'selection__freight_air_booking__service_level%'
              OR name LIKE 'selection__freight_sea_booking__service_level%'
              OR name LIKE 'selection__freight_sea_hbl__service_level%'
          );
    """)

    # 2. Clean up orphaned selection records from ir_model_fields_selection
    cr.execute("""
        DELETE FROM ir_model_fields_selection s
        USING ir_model_fields f
        WHERE s.field_id = f.id
          AND f.ttype != 'selection';
    """)

    # 3. Update ir_model_fields ttype for service_level to 'selection'
    cr.execute("""
        UPDATE ir_model_fields
        SET ttype = 'selection'
        WHERE name = 'service_level'
          AND model IN (
              'freight.air.booking',
              'freight.air.hawb',
              'freight.air.shipment.info.mixin',
              'freight.sea.booking',
              'freight.sea.hbl',
              'freight.sea.shipment.info.mixin'
          );
    """)

    # 4. Normalize existing stored values in tables to lowercase ('p1', 'p2', 'p3', 'p4')
    tables = [
        'freight_sea_booking',
        'freight_sea_hbl',
        'freight_air_booking',
        'freight_air_hawb',
    ]
    for table in tables:
        cr.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table}' AND column_name = 'service_level';
        """)
        if cr.fetchone():
            cr.execute(f"""
                UPDATE {table}
                SET service_level = LOWER(service_level)
                WHERE service_level IS NOT NULL;
            """)

    _logger.info("Migration 18.0.1.3: Standardized service_level successfully.")
