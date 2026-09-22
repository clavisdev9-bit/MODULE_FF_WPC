from odoo import api, fields, models


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

    # FF-79: metadata klasifikasi transaksi (Air/Sea, Export/Import, FCL/LCL
    # khusus Sea) -- dipakai _get_matching_job_types() untuk mencari kandidat
    # Job Type yang cocok dengan sebuah transaksi (murni bantuan filter/
    # auto-fill di Booking/Job, BUKAN formula permanen 1:1), tanpa business
    # logic pernah bergantung pada code/name Job Type itu sendiri.
    business_type = fields.Selection(
        selection=[
            ('sea', 'Sea'),
            ('air', 'Air'),
        ],
        string='Business Type',
    )
    freight_type = fields.Selection(
        selection=[
            ('export', 'Export'),
            ('import', 'Import'),
        ],
        string='Direction',
    )
    sea_ship_mode = fields.Selection(
        selection=[
            ('fcl', 'FCL'),
            ('lcl', 'LCL'),
        ],
        string='Sea Ship Mode',
        help='Hanya relevan ketika Business Type = Sea (FCL/LCL). '
             'Dikosongkan untuk Business Type = Air.',
    )

    @api.onchange('business_type')
    def _onchange_business_type_clear_sea_ship_mode(self):
        for job_type in self:
            if job_type.business_type != 'sea':
                job_type.sea_ship_mode = False

    @api.model
    def _get_matching_job_types(self, business_type, freight_type, sea_ship_mode=False):
        """Cari SEMUA Job Type aktif yang cocok dengan klasifikasi transaksi
        (business_type/freight_type, + sea_ship_mode khusus Sea).

        Cardinality klasifikasi->Job Type TIDAK diasumsikan 1:1 -- bisa
        mengembalikan 0, 1, atau lebih dari 1 record aktif dengan klasifikasi
        yang sama (mis. beda Job Type untuk kebutuhan modul/departemen yang
        sama-sama Sea/Export/FCL). Caller (onchange/helper di Booking/Job)
        yang menentukan tindakan: auto-fill hanya kalau hasilnya tepat 1,
        selain itu dibiarkan kosong untuk dipilih manual oleh user dari
        pilihan yang sudah difilter.

        Domain dibangun murni dari nilai transaksi -- tidak pernah
        mencocokkan berdasarkan code/name Job Type."""
        if not business_type or not freight_type:
            return self.browse()
        domain = [
            ('active', '=', True),
            ('business_type', '=', business_type),
            ('freight_type', '=', freight_type),
        ]
        if business_type == 'sea':
            domain.append(('sea_ship_mode', '=', sea_ship_mode))
        return self.search(domain)
