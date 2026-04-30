from odoo import fields, models


class AirWaybillTransactionReceipt(models.Model):
    _name = "freight.air.waybill.transaction.receipt"
    _description = "Air Waybill Transaction Receipt"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class AirWaybillTransactionRelease(models.Model):
    _name = "freight.air.waybill.transaction.release"
    _description = "Air Waybill Transaction Release"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class AirWaybillTransactionReservation(models.Model):
    _name = "freight.air.waybill.transaction.reservation"
    _description = "Air Waybill Transaction Reservation"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class AirWaybillTransactionIssueToAgent(models.Model):
    _name = "freight.air.waybill.transaction.issue.to.agent"
    _description = "Air Waybill Transaction Issue To Agent"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class AirWaybillTransactionReturnFromAgent(models.Model):
    _name = "freight.air.waybill.transaction.return.from.agent"
    _description = "Air Waybill Transaction Return From Agent"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class AirWaybillTransactionCancellation(models.Model):
    _name = "freight.air.waybill.transaction.cancellation"
    _description = "Air Waybill Transaction Cancellation"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)


class AirWaybillTransactionLost(models.Model):
    _name = "freight.air.waybill.transaction.lost"
    _description = "Air Waybill Transaction Lost"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Active", default=True)
