import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """FF-80: standarisasi Salesperson lewat `user_id -> res.users` di
    freight.sea.booking / freight.sea.job / freight.air.booking /
    freight.air.job -- menggantikan `salesman_id` lama (Sea: hr.employee,
    Air: res.users sudah benar tapi field lama).

    HARUS post-migrate: kolom `user_id` baru ditambahkan lewat _auto_init
    module upgrade (di antara pre-migrate dan post-migrate) -- lihat pola
    yang sama di migrations/18.0.1.7/post-migrate.py. Kolom `salesman_id`
    lama TIDAK di-drop oleh Odoo secara otomatis hanya karena field
    Python-nya dihapus, jadi datanya masih bisa dibaca di sini.

    Sea: salesman_id menyimpan hr_employee.id -- resolve ke
    hr_employee.user_id. Kalau employee tidak punya linked user, JANGAN
    menebak -- user_id baru dibiarkan kosong dan dicatat di log.

    Air: salesman_id sudah menyimpan res_users.id langsung -- copy 1:1.
    """
    for table, model_label in (
        ("freight_sea_booking", "Sea Booking"),
        ("freight_sea_job", "Sea Job"),
    ):
        cr.execute(
            f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'salesman_id'
            """,
            (table,),
        )
        if not cr.fetchone():
            _logger.info(
                "FF-80: %s (%s) has no legacy salesman_id column, skipping.",
                model_label, table,
            )
            continue

        cr.execute(
            f"""
            UPDATE {table} t
            SET user_id = e.user_id
            FROM hr_employee e
            WHERE t.salesman_id = e.id
              AND e.user_id IS NOT NULL
              AND t.user_id IS NULL
            """
        )
        _logger.info(
            "FF-80: %s -- resolved user_id from hr.employee for %s row(s).",
            model_label, cr.rowcount,
        )

        cr.execute(
            f"""
            SELECT t.id, t.salesman_id FROM {table} t
            JOIN hr_employee e ON e.id = t.salesman_id
            WHERE t.salesman_id IS NOT NULL
              AND t.user_id IS NULL
              AND e.user_id IS NULL
            """
        )
        unresolved = cr.fetchall()
        if unresolved:
            _logger.warning(
                "FF-80: %s -- %s row(s) have salesman_id pointing to an "
                "hr.employee WITHOUT a linked user. user_id left empty "
                "(not guessed): %s",
                model_label, len(unresolved), unresolved,
            )

    for table, model_label in (
        ("freight_air_booking", "Air Booking"),
        ("freight_air_job", "Air Job"),
    ):
        cr.execute(
            f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'salesman_id'
            """,
            (table,),
        )
        if not cr.fetchone():
            _logger.info(
                "FF-80: %s (%s) has no legacy salesman_id column, skipping.",
                model_label, table,
            )
            continue

        cr.execute(
            f"""
            UPDATE {table}
            SET user_id = salesman_id
            WHERE salesman_id IS NOT NULL
              AND user_id IS NULL
            """
        )
        _logger.info(
            "FF-80: %s -- copied salesman_id directly to user_id for %s row(s).",
            model_label, cr.rowcount,
        )
