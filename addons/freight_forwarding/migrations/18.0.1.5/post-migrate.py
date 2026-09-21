import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.5:
    1. Seed/ensure the 'Airline' res.partner.category has freight_role_code
       ='airline', matching the same technical-role pattern already applied
       to Shipping Line in 18.0.1.4.
    2. freight.airline.partner_id was originally added as a required field
       on the freight.airline model at this version, with legacy records
       only holding the old 'name' column. That model has since been fully
       removed (ff-68), so this script no longer relies on the ORM for
       freight.airline - it manages the partner_id column and row updates
       via raw SQL so it still works when catching up straight to HEAD.
    """
    _logger.info("Migration 18.0.1.5: seeding freight_role_code on Airline partner category...")
    env = api.Environment(cr, SUPERUSER_ID, {})

    category = env['res.partner.category'].search([('name', '=', 'Airline')], limit=1)
    if category:
        category.write({'freight_role_code': 'airline', 'is_freight_role': True})
    else:
        category = env['res.partner.category'].create({
            'name': 'Airline',
            'freight_role_code': 'airline',
            'is_freight_role': True,
        })

    if not _table_exists(cr, 'freight_airline'):
        _logger.info("freight_airline table not found - nothing to migrate.")
        return

    if not _column_exists(cr, 'freight_airline', 'partner_id'):
        cr.execute("ALTER TABLE freight_airline ADD COLUMN partner_id integer REFERENCES res_partner(id)")
        _logger.info("Migration 18.0.1.5: added partner_id column to freight_airline")

    _logger.info("Migration 18.0.1.5: linking existing Airline records to a Business Party...")
    cr.execute("SELECT id, name FROM freight_airline WHERE partner_id IS NULL")
    rows = cr.fetchall()
    for airline_id, legacy_name in rows:
        partner = env['res.partner'].create({
            'name': legacy_name or 'Unnamed Airline',
            'is_company': True,
            'category_id': [(4, category.id)],
        })
        cr.execute(
            "UPDATE freight_airline SET partner_id = %s WHERE id = %s",
            (partner.id, airline_id),
        )
        _logger.info(
            "Migration 18.0.1.5: linked freight.airline #%s (%s) to new partner #%s",
            airline_id, legacy_name, partner.id,
        )

    _logger.info("Migration 18.0.1.5: done.")


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())