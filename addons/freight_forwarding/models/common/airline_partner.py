from odoo import api, fields, models


class ResPartnerAirline(models.Model):
    _inherit = 'res.partner'

    is_airline = fields.Boolean(
        string='Is Airline',
        compute='_compute_is_airline',
        store=True,
    )

    airline_code = fields.Char(string='Airline Code', size=3)
    airline_identifier = fields.Char(string='Airline ID')
    airline_iata_code = fields.Char(string='IATA Code')
    airline_commission_percentage = fields.Float(string='Commission Percentage')
    airline_terminal = fields.Char(string='Terminal')
    airline_neutral_awb = fields.Boolean(string='Neutral AWB')
    airline_column_offset = fields.Integer(string='Column Offset')
    airline_row_offset = fields.Integer(string='Row Offset')
    airline_ccn = fields.Boolean(string='CCN')
    airline_left_margin = fields.Float(string='Left Margin')
    airline_top_margin = fields.Float(string='Top Margin')
    airline_analysis_code = fields.Char(string='Analysis Code')

    @api.depends('category_id.freight_role_code')
    def _compute_is_airline(self):
        for rec in self:
            rec.is_airline = any(
                c.freight_role_code == 'airline' for c in rec.category_id
            )
