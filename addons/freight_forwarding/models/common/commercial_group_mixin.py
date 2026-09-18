from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightCommercialGroupMixin(models.AbstractModel):
    """Mixin bersama untuk Booking dan Jobsheet (Sea & Air) — FF-73.

    Sebelumnya, commercial group (root quotation + seluruh currency variant-nya)
    hanya bisa diketahui lewat snapshot `sale_order_ids` yang diisi sekali waktu
    convert. Mixin ini menjadikan root quotation (`root_quotation_id`) sebagai
    anchor eksplisit, sehingga commercial group bisa selalu didapat ulang secara
    live (root + `root.variant_ids`) — termasuk currency variant yang dibuat
    SETELAH Booking/Jobsheet sudah ada.

    `sale_order_ids` (masing-masing didefinisikan di model konkretnya sendiri,
    bukan di mixin ini) tetap dipertahankan untuk compatibility finance/report/
    analytic — mixin ini hanya memvalidasi isinya tidak keluar dari commercial
    group yang sama.
    """

    _name = "freight.commercial.group.mixin"
    _description = "Freight Commercial Group Mixin"

    root_quotation_id = fields.Many2one(
        "sale.order",
        string="Root Quotation",
        index=True,
        help="Quotation utama (root) yang menjadi anchor commercial group "
             "untuk record ini. Untuk currency variant, ini selalu menunjuk "
             "ke root-nya, bukan ke variant itu sendiri.",
    )

    def _get_root_quotation(self):
        """Root quotation commercial group. Subclass yang bisa mendapatkan
        root secara tidak langsung (misal Jobsheet Export lewat Booking-nya)
        WAJIB override method ini, bukan cuma mengandalkan root_quotation_id."""
        self.ensure_one()
        return self.root_quotation_id

    def _get_commercial_group(self):
        """Root quotation + seluruh currency variant-nya. Live query, bukan
        snapshot — currency variant yang dibuat kapan pun akan selalu ikut."""
        self.ensure_one()
        root = self._get_root_quotation()
        if not root:
            return self.env["sale.order"]
        return root | root.variant_ids

    @api.constrains("sale_order_ids")
    def _check_sale_order_ids_in_commercial_group(self):
        for rec in self:
            if not rec.sale_order_ids:
                continue
            root = rec._get_root_quotation()
            if not root:
                # root_quotation_id belum/tidak terisi (data lama yang belum
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
