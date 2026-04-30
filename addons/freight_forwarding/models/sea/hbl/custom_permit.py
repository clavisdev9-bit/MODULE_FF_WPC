from odoo import fields, models


class SeaHBLCustomPermit(models.Model):
    _name = "freight.sea.hbl.custom.permit"
    _description = "Sea Jobsheet Custom Permit"
    _rec_name = "hbl_id"

    hbl_id = fields.Many2one(
        "freight.sea.hbl",
        string="Jobsheet No",
        required=True,
        ondelete="cascade",
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    no_document = fields.Char(string="No Document", required=True)
    description = fields.Text(string="Description")
    document = fields.Binary(string="Document", attachment=True)
    document_filename = fields.Char(string="Document Filename")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("approve", "Approve"),
            ("process", "Process"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
    )

    def action_approve(self):
        self.write({"status": "approve"})

    def action_process(self):
        self.write({"status": "process"})

    def action_cancel(self):
        self.write({"status": "cancel"})

    def action_draft(self):
        self.write({"status": "draft"})