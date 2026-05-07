from odoo import api, fields, models


class SeaCargoInfoMixin(models.AbstractModel):
    _name = "freight.sea.cargo.info.mixin"
    _description = "Sea Cargo Info Mixin"

    uom = fields.Selection(
        [
            ("box", "Box / Load"),
            ("container", "Container"),
        ],
        string="Unit of Measure",
        required=True,
    )

    # Box / Pallet / Load
    container_type_id = fields.Many2one(
        "freight.container.type",
        string="Container Type",
    )

    container_no = fields.Char(string="Container No.")

    package_type_id = fields.Many2one(
        "stock.package.type",
        string="Package Type",
    )

    seal_no = fields.Integer(string="Seal No.")

    # Qty & Type
    types_of_cargo = fields.Many2one(
        "freight.cargo.type",
        string="Types of Cargo",
    )
    quantity = fields.Integer(string="Quantity")

    # Dimension
    length = fields.Float(string="Length (cm)")
    width = fields.Float(string="Width (cm)")
    height = fields.Float(string="Height (cm)")

    # Weight & Volume
    gross_weight = fields.Float(string="Gross Weight (Kg)")
    net_weight = fields.Float(string="Net Weight (Kg)")
    volume = fields.Float(
        string="Volume (CBM)",
        readonly=True,
        store=True,
        digits=(16, 6),
    )
    volume_manual = fields.Boolean(
        string="Manual Volume",
        help="Check to manually set volume and bypass automatic calculation",
    )
    total_volume = fields.Float(string="Total Volume (CBM)")

    # Environmental Condition
    harmonize = fields.Char(string="Harmonize")
    temperature = fields.Char(string="Temperature")
    ventilation = fields.Char(string="Ventilation")
    humidity = fields.Char(string="Humidity")

    # Dangerous Goods
    has_dangerous_goods = fields.Boolean(string="Has Dangerous Goods")

    # Regulatory Classification
    imdg_code = fields.Char(string="IMDG Code")
    class_number = fields.Char(string="Class Number")
    packing_group = fields.Char(string="Packing Group")
    a_number = fields.Char(string="A Number")

    # Safety and Handling
    flash_point = fields.Char(string="Flash Point")
    material_description = fields.Char(string="Material Description")

    @api.onchange("length", "width", "height")
    def _onchange_volume(self):
        """Auto-calculate volume in CBM based on dimensions in cm when not manual.
        Formula: CBM = (Length × Width × Height) ÷ 1,000,000
        """
        if not self.volume_manual:
            if self.length and self.width and self.height:
                # Convert from cm³ to m³ (CBM)
                self.volume = (self.length * self.width * self.height) / 1_000_000
            else:
                self.volume = 0.0

    @api.onchange("volume_manual")
    def _onchange_volume_manual(self):
        """Reset volume calculation when toggling manual mode off."""
        if not self.volume_manual:
            # Recalculate if dimensions are available
            if self.length and self.width and self.height:
                self.volume = (self.length * self.width * self.height) / 1_000_000
            else:
                self.volume = 0.0
