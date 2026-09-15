from odoo import api, fields, models, _


class FreightSeaChargeTable(models.Model):
    _name = 'freight.sea.charge.table'
    _description = 'Freight Sea Charge Table'
    _rec_name = 'number'
    _order = 'id desc'

    number = fields.Char(string='Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    description = fields.Char(string='Description')
    job_type_id = fields.Many2one('freight.job.type', string='Job Type')
    module_code = fields.Char(related='job_type_id.module_code', string='Module', readonly=True, store=True)
    estimated_transit_time = fields.Char(string='Estimated Transit Time')
    frequency = fields.Char(string='Frequency')
    customer_id = fields.Many2one('res.partner', string='Customer')
    port_loading_id = fields.Many2one('freight.port', string='Port Loading')
    port_discharge_id = fields.Many2one('freight.port', string='Port Discharge')
    via_port_id = fields.Many2one('freight.port', string='Via Port')
    destination_city_id = fields.Many2one('res.city', string='Destination City')
    valid = fields.Boolean(string='Valid')
    standard_charge = fields.Boolean(string='Standard Charge')
    effective_date = fields.Date(string='Effective Date')
    expiry_date = fields.Date(string='Expiry Date')
    freight_collect = fields.Boolean(string='Frt Collect')
    note = fields.Text(string='Note')
    note_code = fields.Char(string='Note Code')
    table_type = fields.Char(string='Table Type', default='S', readonly=True)
    active = fields.Boolean(string='Active', default=True)

    line_ids = fields.One2many('freight.sea.charge.table.line', 'charge_table_id', string='Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', _('New')) == _('New'):
                vals['number'] = self.env['ir.sequence'].next_by_code('freight.sea.charge.table') or _('New')
        return super().create(vals_list)
