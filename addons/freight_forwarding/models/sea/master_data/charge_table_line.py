from odoo import fields, models


class FreightSeaChargeTableLine(models.Model):
    _name = 'freight.sea.charge.table.line'
    _description = 'Freight Sea Charge Table Line'

    charge_table_id = fields.Many2one(
        'freight.sea.charge.table', required=True, ondelete='cascade',
    )
    charge_code_id = fields.Many2one('freight.charge.code', string='Charge Code')
    description = fields.Char(related='charge_code_id.item_description', string='Description', readonly=True)
    qty = fields.Float(string='Qty')
    cargo_type = fields.Selection([
        ('fcl', 'FCL'),
        ('lcl', 'LCL'),
    ], string='Cargo Type')
    dg_level = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
    ], string='DG Level')
    uom_id = fields.Many2one('uom.uom', string='UOM')
    charge_flag = fields.Boolean(string='Charge Flag')
    vat_id = fields.Many2one('account.tax', string='VAT')
    prepaid_collect = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect'),
    ], string='Prepaid/Collect')
    charge_unit = fields.Selection([
        ('container', 'CONTAINER'),
        ('rev_ton', 'REV TON'),
        ('rev_ton_rnd_up', 'REV TON RND UP'),
        ('rev_ton_custom', 'REV TON CUSTOM'),
        ('shipment', 'SHIPMENT'),
        ('house', 'HOUSE'),
        ('subhouse_bl', 'SUBHOUSE B/L'),
        ('volume', 'VOLUME'),
        ('weight', 'WEIGHT'),
        ('pcs', 'PCS'),
        ('block_4m3', 'BLOCK OF 4 M3'),
        ('block_3m3', 'BLOCK OF 3 M3'),
        ('invoice_charge_weight', 'INVOICE CHARGE WEIGHT'),
    ], string='Charge Unit')
    container_type_id = fields.Many2one('freight.container.type', string='Container Type')
    rate_type = fields.Selection([
        ('break_point', 'Break Point'),
        ('std_rate', 'Std Rate'),
        ('flat_amt', 'Flat Amt'),
    ], string='Rate Type')
    currency_id = fields.Many2one('res.currency', string='Currency')
    minimum_amount = fields.Float(string='Minimum Amount')
    amount = fields.Float(string='Amount')
    cost = fields.Float(string='Cost')
    percent = fields.Float(string='Percent')
