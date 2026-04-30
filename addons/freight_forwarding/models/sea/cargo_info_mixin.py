from odoo import fields, models


class SeaCargoInfoMixin(models.AbstractModel):
    _name = "freight.sea.cargo.info.mixin"
    _description = "Sea Cargo Info Mixin"

    package_type = fields.Selection(
        [
            ("load", "Box / Load"),
            ("container", "Container / Box"),
        ],
        string="Package Type",
        required=True,
    )

    # Box / Pallet / Load
    size_package = fields.Many2one(
        "stock.package.type",
        string="Size/Package",
        required=True,
    )
    container_no = fields.Char(string="Container No.")
    stamp_no = fields.Integer(string="Stamp No.")
    container_box_type_id = fields.Many2one(
        "freight.container.type",
        string="Container/Box Type",
    )

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
    volume = fields.Float(string="Volume (CBM)")
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