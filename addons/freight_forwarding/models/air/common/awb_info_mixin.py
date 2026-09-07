from odoo import fields, models

class FreightAirAwbInfoMixin(models.AbstractModel):
    _name = 'freight.air.awb.info.mixin'
    _description = 'Air Freight AWB Info Mixin'

    shipper_id = fields.Many2one('res.partner', string='Shipper')
    shipper_address = fields.Char(
        string='Shipper Address',
        related='shipper_id.contact_address',
        readonly=True,
    )
    consignee_id = fields.Many2one('res.partner', string='Consignee')
    consignee_address = fields.Char(
        string='Consignee Address',
        related='consignee_id.contact_address',
        readonly=True,
    )
    notify_party_id = fields.Many2one('res.partner', string='Notify Party')
    notify_address = fields.Char(
        string='Notify Address',
        related='notify_party_id.contact_address',
        readonly=True,
    )
    coloader_id = fields.Many2one('res.partner', string='Coloader')
    coloader_address = fields.Char(
        string='Coloader Address',
        related='coloader_id.contact_address',
        readonly=True,
    )
    agent_id = fields.Many2one('res.partner', string='Agent')
    agent_address = fields.Char(
        string='Agent Address',
        related='agent_id.contact_address',
        readonly=True,
    )
    overseas_agent_id = fields.Many2one('res.partner', string='Overseas Agent')
    overseas_agent_address = fields.Char(
        string='Overseas Agent Address',
        related='overseas_agent_id.contact_address',
        readonly=True,
    )
