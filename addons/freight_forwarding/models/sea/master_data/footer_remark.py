from odoo import fields, models


class FreightFooterRemark(models.Model):
    _name = "freight.footer.remark"
    _description = "Freight Footer Remark"
    _rec_name = "booking_remark"

    _sql_constraints = [

        (
            "remark_unique",
            "UNIQUE(booking_remark)",
            "Booking Remark must be unique!",
        ),
    ]

    booking_remark = fields.Char(string="Booking Remark", required=True)
    warehouse_remark = fields.Char(string="Warehouse Remark")
    active = fields.Boolean(string="Active", default=True)
