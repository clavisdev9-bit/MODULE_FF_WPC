from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightCommercialGroupMixin(models.AbstractModel):
    """Mixin bersama untuk Booking dan Job (Sea & Air) — FF-73 / FF-75.

    `source_quotation_id` menyimpan Quotation yang menjadi SOURCE ketika
    record ini pertama dibuat — bukan commercial root untuk seluruh
    keluarga Master/House.

    Booking dan House bisa punya `source_quotation_id` sendiri (House
    tidak dipaksa mengikuti source_quotation_id milik Booking/Master-nya,
    FF-75). Master TIDAK memiliki canonical commercial source apa pun --
    `source_quotation_id` Master selalu kosong dan TIDAK boleh di-resolve
    lewat Booking (Master bukan commercial owner Quotation). Satu
    pengecualian: Air Direct (di luar scope hierarchy Master/House FF-75)
    punya fallback khusus lewat `booking_id._get_source_quotation()` kalau
    `source_quotation_id`-nya sendiri kosong -- lihat
    `freight.air.job._get_source_quotation()`.

    Field ini tetap dipakai sebagai anchor untuk mendapatkan commercial group
    (root + `root.variant_ids`) secara live milik record itu SENDIRI.

    `sale_order_ids` (masing-masing didefinisikan di model konkretnya sendiri,
    bukan di mixin ini) tetap dipertahankan untuk compatibility finance/report/
    analytic — mixin ini hanya memvalidasi isinya tidak keluar dari commercial
    group yang sama.
    """

    _name = "freight.commercial.group.mixin"
    _description = "Freight Commercial Group Mixin"

    source_quotation_id = fields.Many2one(
        "sale.order",
        string="Source Quotation",
        index=True,
        help="Quotation yang menjadi SOURCE ketika record ini pertama dibuat. "
             "Untuk currency variant, ini selalu menunjuk ke root-nya, bukan "
             "ke variant itu sendiri. Tidak berarti seluruh House di bawah "
             "Master yang sama berasal dari Quotation ini.",
    )

    def _get_source_quotation(self):
        """Source quotation milik record ini sendiri (base impl, dipakai
        apa adanya oleh Booking Sea/Air dan Sea Job -- Sea tidak punya
        konsep Direct, jadi Sea Job TIDAK override method ini sama sekali,
        murni field sendiri, tanpa fallback lewat booking_id).

        Subclass yang bisa mendapatkan source secara tidak langsung WAJIB
        override method ini secara eksplisit dan sesempit mungkin -- jangan
        sampai fallback berlaku untuk Master/House (keduanya harus selalu
        resolve dari source_quotation_id sendiri, TIDAK boleh lewat
        Booking). Satu-satunya override saat ini adalah Air Job untuk
        shipment_type == 'direct' (lihat freight.air.job._get_source_quotation),
        karena Direct adalah standalone Job yang bisa dibuat lewat Booking
        tanpa source_quotation_id sendiri -- di luar scope FF-75, behavior
        existing dipertahankan apa adanya."""
        self.ensure_one()
        return self.source_quotation_id

    def _get_commercial_group(self):
        """Source quotation + seluruh currency variant-nya. Live query, bukan
        snapshot — currency variant yang dibuat kapan pun akan selalu ikut."""
        self.ensure_one()
        root = self._get_source_quotation()
        if not root:
            return self.env["sale.order"]
        return root | root.variant_ids

    @api.constrains("sale_order_ids")
    def _check_sale_order_ids_in_commercial_group(self):
        for rec in self:
            if not rec.sale_order_ids:
                continue
            root = rec._get_source_quotation()
            if not root:
                # source_quotation_id belum/tidak terisi (data lama yang belum
                # di-backfill, atau kasus lain) — jangan blokir, tidak ada
                # commercial group yang bisa dijadikan acuan validasi.
                continue
            group = rec._get_commercial_group()
            invalid = rec.sale_order_ids - group
            if invalid:
                raise ValidationError(
                    "Sales Order %s bukan bagian dari commercial group quotation %s."
                    % (invalid.mapped("name"), root.name)
                )
