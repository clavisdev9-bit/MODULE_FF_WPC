from odoo import fields, models


class ResPartnerDeliveryInfo(models.Model):
    _inherit = 'res.partner'

    special_instruction = fields.Text(string='Special Instruction')
    delivery_instruction = fields.Text(string='Delivery Instruction')
    billing_instruction = fields.Text(string='Billing Instruction')
    cfs_charge_instruction = fields.Text(string='CFS Charge Instruction')
