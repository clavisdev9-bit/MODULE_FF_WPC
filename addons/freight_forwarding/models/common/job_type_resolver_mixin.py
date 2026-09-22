from odoo import api, fields, models


class FreightJobTypeResolverMixin(models.AbstractModel):
    """FF-79: mixin untuk Booking/Job Sea & Air yang menyediakan
    `job_type_id` -- Many2one STORED biasa, bisa dipilih/diubah manual oleh
    user (mis. "Change Job Type"), BUKAN computed field.

    Classification (freight_type + ship_mode khusus Sea; business_type
    implisit dari model lewat `_job_type_business_type`) hanya dipakai
    sebagai bantuan, bukan formula permanen untuk job_type_id:
    1. `_get_job_type_candidates()` -- cari Job Type aktif yang cocok.
    2. Domain pilihan Job Type di view (ditulis statis per view XML,
       karena business_type konstan per model -- lihat views/sea/.. dan
       views/air/..).
    3. `_onchange_job_type_classification()` -- auto-fill HANYA kalau
       kandidatnya tepat satu; kalau job_type_id yang sedang terisi sudah
       tidak cocok dengan klasifikasi baru, dikosongkan lagi. Kalau
       kandidat >1 (cardinality klasifikasi->Job Type tidak 1:1), TIDAK
       pernah menebak -- job_type_id dibiarkan kosong untuk dipilih manual.

    Model yang inherit WAJIB set `_job_type_business_type` ('sea'/'air')
    dan sudah punya field `freight_type`. Untuk 'sea', field `ship_mode`
    (FCL/LCL) juga dipakai; untuk 'air', `ship_mode` model itu sendiri
    (semantic-nya routing order/free hands/transit, bukan FCL/LCL) sengaja
    TIDAK dipakai untuk klasifikasi.

    Auto-fill berlaku lewat DUA jalur yang berbagi resolver yang sama
    (`_resolve_job_type_id`/`_get_job_type_candidates`), supaya aturan
    0/1/>1 kandidat konsisten baik lewat UI maupun lewat Python:
    - `_onchange_job_type_classification()` -- jalur UI (record sudah ada
      di memori, baca field langsung).
    - `create()` -- jalur programmatic (Quotation -> Booking, Quotation ->
      Job direct, Booking -> Create Job, dst.). `job_type_id` yang SUDAH
      diberikan eksplisit di vals (key ada, apa pun isinya) tidak pernah
      ditimpa oleh resolver.
    """

    _name = 'freight.job.type.resolver.mixin'
    _description = 'Freight Job Type Resolver Mixin'

    _job_type_business_type = None

    job_type_id = fields.Many2one(
        'freight.job.type',
        string='Job Type',
    )

    def _get_job_type_classification(self):
        self.ensure_one()
        business_type = self._job_type_business_type
        sea_ship_mode = self.ship_mode if business_type == 'sea' else False
        return business_type, self.freight_type, sea_ship_mode

    def _get_job_type_candidates(self):
        """Recordset Job Type aktif yang cocok dengan klasifikasi record
        ini SAAT INI (bisa 0, 1, atau banyak record)."""
        self.ensure_one()
        business_type, freight_type, sea_ship_mode = self._get_job_type_classification()
        return self.env['freight.job.type']._get_matching_job_types(
            business_type, freight_type, sea_ship_mode
        )

    @api.model
    def _resolve_job_type_id_from_vals(self, vals):
        """Versi `_get_job_type_candidates()` yang bekerja dari `vals`
        create() mentah (belum jadi record) -- dipakai `create()` supaya
        logic pencarian kandidat TIDAK diduplikasi antara jalur onchange
        (UUI) dan jalur programmatic (create). Sama seperti onchange:
        kandidat tepat satu -> return id-nya; 0 atau >1 -> return False
        (dibiarkan kosong, tidak pernah menebak)."""
        business_type = self._job_type_business_type
        sea_ship_mode = vals.get('ship_mode') if business_type == 'sea' else False
        candidates = self.env['freight.job.type']._get_matching_job_types(
            business_type, vals.get('freight_type'), sea_ship_mode
        )
        return candidates.id if len(candidates) == 1 else False

    @api.onchange('freight_type', 'ship_mode')
    def _onchange_job_type_classification(self):
        """Bantu isi/bersihkan job_type_id saat klasifikasi berubah:
        - job_type_id yang sedang terisi tapi sudah tidak cocok dengan
          klasifikasi baru -> dikosongkan.
        - kandidat tepat satu -> auto-fill.
        - kandidat 0 atau >1 -> dibiarkan apa adanya (kosong), user pilih
          manual dari domain di view."""
        for record in self:
            candidates = record._get_job_type_candidates()
            if record.job_type_id and record.job_type_id not in candidates:
                record.job_type_id = False
            if not record.job_type_id and len(candidates) == 1:
                record.job_type_id = candidates

    @api.model_create_multi
    def create(self, vals_list):
        """Jalur programmatic (Quotation -> Booking, Quotation -> Job
        direct, dst.): onchange TIDAK pernah jalan saat record dibuat
        lewat Python, jadi auto-fill job_type_id perlu di-resolve di sini
        juga -- pakai resolver yang SAMA dengan onchange
        (`_resolve_job_type_id_from_vals`), bukan logic terpisah.

        `job_type_id` yang sudah diberikan eksplisit di vals (key ada,
        termasuk kalau isinya False/kosong secara sengaja) TIDAK PERNAH
        ditimpa -- resolver hanya mengisi saat key-nya benar-benar tidak
        ada di vals."""
        for vals in vals_list:
            if 'job_type_id' not in vals:
                resolved = self._resolve_job_type_id_from_vals(vals)
                if resolved:
                    vals['job_type_id'] = resolved
        return super().create(vals_list)
