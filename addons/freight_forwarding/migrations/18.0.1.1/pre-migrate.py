import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.1:
    1. Konversi freight_vessel.flag dari varchar ke integer (Many2one res.country)
    2. Migrasi FK shipment_type_id dari freight_delivery_type ke freight_shipment_type
       pada tabel freight_sea_booking_shipment_info dan freight_sea_hbl_shipment_info
    3. Bersihkan kolom legacy yang pernah dibuat sebagai Char sebelum dijadikan FK
       ke account.incoterms dan freight.location.
    4. Bersihkan orphan selection metadata untuk field yang diubah menjadi Boolean (misal do_ready_on).
    """
    _migrate_vessel_flag(cr)
    _migrate_shipment_type_fk(cr)
    _migrate_legacy_fk_columns(cr)
    _clean_orphan_selection_fields(cr)


def _clean_orphan_selection_fields(cr):
    """Hapus metadata selection untuk field yang telah diubah ke Boolean agar tidak error saat upgrade."""
    _logger.info("Migration: cleaning orphan ir_model_fields_selection records...")
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields.selection'
          AND res_id IN (
              SELECT s.id
              FROM ir_model_fields_selection s
              JOIN ir_model_fields f ON s.field_id = f.id
              WHERE f.model = 'freight.sea.hbl' AND f.name = 'do_ready_on'
          )
    """)
    cr.execute("""
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'freight.sea.hbl' AND name = 'do_ready_on'
        )
    """)
    cr.execute("""
        UPDATE ir_model_fields
        SET ttype = 'boolean'
        WHERE model = 'freight.sea.hbl' AND name = 'do_ready_on'
    """)
    _logger.info("Migration: orphan selection records cleaned successfully.")


def _migrate_vessel_flag(cr):
    """Konversi freight_vessel.flag dari varchar ke integer."""
    cr.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'freight_vessel'
          AND column_name = 'flag'
    """)
    row = cr.fetchone()
    if row and row[0] in ('character varying', 'text', 'varchar'):
        _logger.info(
            "Migration: converting freight_vessel.flag from varchar to integer "
            "(clearing existing text values)"
        )
        cr.execute(
            "ALTER TABLE freight_vessel ALTER COLUMN flag TYPE integer USING NULL"
        )
        _logger.info("Migration: freight_vessel.flag converted successfully.")
    else:
        _logger.info("Migration: freight_vessel.flag already integer, skipping.")


def _migrate_shipment_type_fk(cr):
    """
    Migrasi FK shipment_type_id dari freight_delivery_type ke freight_shipment_type.
    Langkah:
      1. Set shipment_type_id = NULL pada kedua tabel (data lama tidak bisa dipakai)
      2. Drop FK constraint lama yang pointing ke freight_delivery_type
    Odoo akan membuat FK baru ke freight_shipment_type saat module init.
    """
    tables = [
        ('freight_sea_booking_shipment_info',
         'freight_sea_booking_shipment_info_shipment_type_id_fkey'),
        ('freight_sea_hbl_shipment_info',
         'freight_sea_hbl_shipment_info_shipment_type_id_fkey'),
    ]

    for table, constraint in tables:
        # Cek apakah constraint masih pointing ke freight_delivery_type
        cr.execute("""
            SELECT confrelid::regclass::text
            FROM pg_constraint
            WHERE conname = %s
        """, (constraint,))
        row = cr.fetchone()

        if row and 'freight_delivery_type' in row[0]:
            _logger.info(
                "Migration: resetting %s.shipment_type_id and dropping old FK "
                "constraint %s (was pointing to freight_delivery_type)",
                table, constraint
            )
            cr.execute(
                "UPDATE {} SET shipment_type_id = NULL "
                "WHERE shipment_type_id IS NOT NULL".format(table)
            )
            cr.execute(
                "ALTER TABLE {} DROP CONSTRAINT IF EXISTS {}".format(table, constraint)
            )
            _logger.info(
                "Migration: %s FK constraint dropped successfully.", table
            )
        else:
            _logger.info(
                "Migration: %s FK already correct or not found, skipping.", table
            )


def _migrate_legacy_fk_columns(cr):
    """Drop legacy varchar columns that previously blocked FK creation."""
    tables = ['freight_sea_booking', 'freight_sea_hbl']
    columns = ['freight_terms', 'depot_id', 'freight_terms_new', 'depot_code', 'depot_id_new']

    for table in tables:
        for column in columns:
            cr.execute("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, column))
            if cr.fetchone():
                _logger.warning(
                    "Migration: dropping legacy column %s on %s before FK re-init",
                    column,
                    table,
                )
                cr.execute(
                    "ALTER TABLE {} DROP COLUMN IF EXISTS {}".format(table, column)
                )
