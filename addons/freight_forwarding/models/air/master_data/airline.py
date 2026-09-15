from odoo import models, fields


class Airline(models.Model):
    _name = 'freight.airline'
    _description = 'Freight Airline'
    _rec_name = 'partner_name'

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Airline Code must be unique!'),
        ('partner_unique', 'UNIQUE(partner_id)', 'This Business Party already has an Airline profile!'),
    ]

    partner_id = fields.Many2one(
        'res.partner', string='Business Party', required=True, ondelete='restrict',
        domain="[('category_id.freight_role_code', '=', 'airline')]",
    )

    code = fields.Char(string='Airline Code', required=True, size=3)
    airline_identifier = fields.Char(string='Airline ID')
    iata_code = fields.Char(string='IATA Code')
    awb_prefix = fields.Char(string='AWB Prefix')

    commission_percentage = fields.Float(string='Commission Percentage')
    terminal = fields.Char(string='Terminal')
    neutral_awb = fields.Boolean(string='Neutral AWB')
    column_offset = fields.Integer(string='Column Offset')
    row_offset = fields.Integer(string='Row Offset')
    ccn = fields.Boolean(string='CCN')
    left_margin = fields.Float(string='Left Margin')
    top_margin = fields.Float(string='Top Margin')
    analysis_code = fields.Char(string='Analysis Code')

    active = fields.Boolean(string='Active', default=True)

    # -------------------------------------------------------------
    # Convenience read-only fields sourced from partner_id.
    # res.partner is the source of truth - these are not duplicated
    # storage, just related passthroughs for display on this form.
    # Note: res.partner has no 'fax' field in this Odoo version, so
    # Fax (present in the Sysfreight reference) is intentionally not
    # reproduced here - adding a standalone fax field would itself
    # be exactly the kind of duplication this model must avoid.
    # -------------------------------------------------------------
    partner_name = fields.Char(related='partner_id.name', string='Company Name', readonly=True)
    street = fields.Char(related='partner_id.street', string='Address', readonly=True)
    city = fields.Char(related='partner_id.city', string='City', readonly=True)
    country_id = fields.Many2one(related='partner_id.country_id', string='Country', readonly=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    website = fields.Char(related='partner_id.website', string='Website', readonly=True)
