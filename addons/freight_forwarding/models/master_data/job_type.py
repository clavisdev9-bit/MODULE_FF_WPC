from odoo import fields, models


class FreightJobType(models.Model):
    _name = 'freight.job.type'
    _description = 'Freight Job Type'
    _rec_name = 'code'

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Job Type Code must be unique!')
    ]

    code = fields.Char(string='Job Type', required=True, size=10)
    name = fields.Char(string='Job Description')
    module_code = fields.Char(string='Module Code')
    active = fields.Boolean(string='Active', default=True)
