from odoo import fields, models


class SeaHBLCargoInfo(models.Model):
    _name = "freight.sea.job.cargo.info"
    _inherit = "freight.sea.cargo.info.mixin"
    _description = "Sea Jobsheet Cargo Info"
    _rec_name = "job_id"

    job_id = fields.Many2one(
        "freight.sea.job",
        string="Jobsheet",
        ondelete="cascade",
    )
    hbl_no = fields.Char(
        string="Jobsheet No.",
        related="job_id.hbl_no",
        store=True,
        readonly=True,
    )
    type = fields.Selection(
        related="job_id.freight_type",
        string="Type",
        store=True,
        readonly=True,
    )
    # FF-75 follow-up: field `freight_type` (related=job_id.container_type)
    # dihapus -- misleading (parent.freight_type sebenarnya berarti
    # Import/Export, lihat field `type` di atas), dan container_type sendiri
    # sudah dihapus dari Job (diganti ship_mode). Tidak ada runtime consumer
    # lain selain definisinya sendiri (dikonfirmasi lewat audit), jadi tidak
    # diganti dengan stored duplicate baru -- consumer yang butuh FCL/LCL
    # harus baca job_id.ship_mode langsung.
    booking_id = fields.Many2one(
        "freight.sea.booking",
        string="Booking",
        related="job_id.booking_id",
        store=True,
        readonly=True,
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="job_id.customer_id",
        store=True,
        readonly=True,
    )
