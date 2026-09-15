import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.5:
    1. Seed/ensure the 'Airline' res.partner.category has freight_role_code
       ='airline', matching the same technical-role pattern already applied
       to Shipping Line in 18.0.1.4. This also backs the pre-existing
       name-based domain on freight.air.flight.routing.mixin.airline_id
       (now switched to the technical code alongside this migration).
    2. freight.airline.partner_id is now required, but existing
       freight.airline records predate this field and only have their old
       'name' column (the field itself is removed from the model in this
       version - the column is not auto-dropped by the framework, so it's
       still readable via raw SQL). For each such record, create a new
       res.partner from that legacy name and link it - a safe, one-to-one
       creation, not an aggressive name-match against existing partners
       (which could wrongly attach to an unrelated existing record).
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

    _logger.info("Migration 18.0.1.5: linking existing Airline records to a Business Party...")
    cr.execute("SELECT id, name FROM freight_airline WHERE partner_id IS NULL")
    rows = cr.fetchall()
    for airline_id, legacy_name in rows:
        partner = env['res.partner'].create({
            'name': legacy_name or 'Unnamed Airline',
            'is_company': True,
            'category_id': [(4, category.id)],
        })
        env['freight.airline'].browse(airline_id).write({'partner_id': partner.id})
        _logger.info(
            "Migration 18.0.1.5: linked freight.airline #%s (%s) to new partner #%s",
            airline_id, legacy_name, partner.id,
        )

    _logger.info("Migration 18.0.1.5: done.")
