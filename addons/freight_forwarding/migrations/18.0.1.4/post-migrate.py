import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.4:
    Ensure the 'Shipping Line' res.partner.category has a stable
    freight_role_code. This category was previously only matched by
    display name (category_id.name = 'Shipping Line') in domains on
    Sea shipping_line_id fields, with no XML data record backing it,
    so any existing tag must be updated in place rather than
    duplicated by a fresh XML-seeded record. Uses the ORM (not raw
    SQL) since res.partner.category.name is a translated field.
    """
    _logger.info("Migration 18.0.1.4: seeding freight_role_code on Shipping Line partner category...")

    env = api.Environment(cr, SUPERUSER_ID, {})
    category = env['res.partner.category'].search([('name', '=', 'Shipping Line')], limit=1)
    if category:
        category.write({'freight_role_code': 'shipping_line', 'is_freight_role': True})
    else:
        env['res.partner.category'].create({
            'name': 'Shipping Line',
            'freight_role_code': 'shipping_line',
            'is_freight_role': True,
        })

    _logger.info("Migration 18.0.1.4: done.")
