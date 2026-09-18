import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE freight_port_destination dest
        SET destination_country_id = city.country_id
        FROM res_city city
        WHERE dest.destination_city_id = city.id
          AND city.country_id IS NOT NULL
          AND (dest.destination_country_id IS NULL
               OR dest.destination_country_id != city.country_id)
    """)
    _logger.info(
        "freight.port.destination: %d records updated with destination_country_id",
        cr.rowcount,
    )
