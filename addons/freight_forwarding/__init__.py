from . import models
from psycopg2 import sql


def post_init_hook(env):
    legacy_tables = [
        "freight_sea_booking_bl_info",
        "freight_sea_booking_notify_party",
    ]
    for table in legacy_tables:
        env.cr.execute(
            sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table))
        )