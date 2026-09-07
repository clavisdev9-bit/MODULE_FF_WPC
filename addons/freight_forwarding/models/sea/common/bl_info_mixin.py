from odoo import api, fields, models


class FreightBlInfoMixin(models.AbstractModel):
    _name = "freight.sea.bl.info.mixin"
    _description = "Freight Sea B/L Info Mixin"

    # Shipper
    shipper_id = fields.Many2one(
        "res.partner",
        string="Shipper",
        domain="[('category_id.name', '=', 'Shipper')]",
    )
    shipper_address = fields.Char(
        string="Shipper Address",
        compute="_compute_shipper_address",
        store=False,
    )

    # Consignee
    consignee_id = fields.Many2one(
        "res.partner",
        string="Consignee",
        domain="[('category_id.name', '=', 'Consignee')]",
    )
    consignee_address = fields.Char(
        string="Consignee Address",
        compute="_compute_consignee_address",
        store=False,
    )

    # Notify Party
    notify_same_as_consignee = fields.Boolean(
        string="Same as Consignee",
        default=False,
    )
    notify_party_id = fields.Many2one(
        "res.partner",
        string="Notify Party",
        domain="[('category_id.name', '=', 'Notify Party')]",
    )
    notify_address = fields.Char(
        string="Notify Address",
        compute="_compute_notify_party_address",
        store=False,
    )
    notify_party_address = fields.Char(
        string="Notify Party Address",
        compute="_compute_notify_party_address",
        store=False,
    )

    # Delivery Agent
    delivery_agent_id = fields.Many2one(
        "res.partner",
        string="Delivery Agent",
        domain="[('category_id.name', '=', 'Delivery Agent')]",
    )
    delivery_agent_address = fields.Char(
        string="Delivery Agent Address",
        compute="_compute_delivery_agent_address",
        store=False,
    )

    def _build_partner_address(self, partner):
        """Build formatted address string dari res.partner record."""
        if not partner:
            return False
        parts = [
            partner.street,
            partner.street2,
            partner.city,
            partner.state_id.name,
            partner.country_id.name,
        ]
        return ", ".join(filter(None, parts))

    @api.depends("shipper_id")
    def _compute_shipper_address(self):
        for rec in self:
            rec.shipper_address = self._build_partner_address(rec.shipper_id)

    @api.depends("consignee_id")
    def _compute_consignee_address(self):
        for rec in self:
            rec.consignee_address = self._build_partner_address(rec.consignee_id)

    @api.depends("notify_party_id")
    def _compute_notify_party_address(self):
        for rec in self:
            addr = self._build_partner_address(rec.notify_party_id)
            rec.notify_party_address = addr
            rec.notify_address = addr
                
    @api.depends("delivery_agent_id")
    def _compute_delivery_agent_address(self):
        for rec in self:
            rec.delivery_agent_address = self._build_partner_address(rec.delivery_agent_id)

    # @api.onchange("notify_same_as_consignee", "consignee_id")
    # def _onchange_notify_same_as_consignee(self):
    #     if self.notify_same_as_consignee:
    #         self.notify_party_id = self.consignee_id
            
    @api.onchange('notify_party_id')
    def _onchange_notify_party_id(self):
        if self.notify_party_id and not self.notify_address:
            addr = self.notify_party_id._display_address() if hasattr(self.notify_party_id, '_display_address') else (self.notify_party_id.street or '')
            self.notify_address = addr
            self.notify_party_address = addr

    def action_same_as_consignee(self):
        self.ensure_one()
        if self.consignee_id:
            self.notify_party_id = self.consignee_id
            addr = self.consignee_address or (self.consignee_id._display_address() if hasattr(self.consignee_id, '_display_address') else '')
            self.notify_address = addr
            self.notify_party_address = addr

