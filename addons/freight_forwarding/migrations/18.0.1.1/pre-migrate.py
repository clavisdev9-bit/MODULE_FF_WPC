import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migrate freight_vessel.flag column from varchar to integer (Many2one res.country).
    Data lama (text seperti "Denmark") tidak bisa dikonversi otomatis ke integer FK,
    sehingga harus di-clear terlebih dahulu.
    """
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
        _logger.info("Migration: freight_vessel.flag column converted successfully.")
    else:
        _logger.info(
            "Migration: freight_vessel.flag is already integer type, skipping."
        )
