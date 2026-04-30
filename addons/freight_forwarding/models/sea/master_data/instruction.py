from odoo import fields, models


class FreightInstruction(models.Model):
    _name = "freight.instruction"
    _description = "Freight Instruction"
    _rec_name = "description"

    _sql_constraints = [
        (
            "instruction_unique",
            "UNIQUE(instruction_type, description)",
            "Instruction must be unique!",
        ),
    ]

    instruction_type = fields.Selection(
        [
            ("depot", "Depot"),
            ("general", "General"),
        ],
        string="Instruction Type",
        required=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
