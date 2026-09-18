import logging

_logger = logging.getLogger(__name__)


def resolve_single_root(root_ids):
    """FF-73: root_ids adalah kumpulan hasil COALESCE(original_quotation_id, id)
    dari SELURUH anggota sale_order_ids sebuah Booking/Jobsheet.

    Mengembalikan root id kalau SELURUH anggota resolve ke EXACTLY satu root
    yang sama. Mengembalikan None kalau tidak ada anggota sama sekali, atau
    kalau anggota resolve ke LEBIH DARI SATU root berbeda -- caller TIDAK
    boleh menebak salah satu (tidak ada MIN/arbitrary pick di sini)."""
    distinct_roots = {root_id for root_id in root_ids if root_id is not None}
    if len(distinct_roots) == 1:
        return next(iter(distinct_roots))
    return None


def _fetch_candidate_roots(cr, main_table, rel_table, fk_col, extra_filter=""):
    """Untuk setiap record di main_table yang root_quotation_id masih kosong
    dan punya minimal satu sale_order_ids, kumpulkan root (COALESCE(
    original_quotation_id, id)) dari SELURUH anggotanya -- bukan cuma salah
    satu (dulu: MIN(sale_order_id))."""
    cr.execute(
        f"""
        SELECT rel.{fk_col} AS record_id,
               array_agg(DISTINCT COALESCE(so.original_quotation_id, so.id)) AS roots
        FROM {rel_table} rel
        JOIN sale_order so ON so.id = rel.sale_order_id
        JOIN {main_table} m ON m.id = rel.{fk_col}
        WHERE m.root_quotation_id IS NULL
        {extra_filter}
        GROUP BY rel.{fk_col}
        """
    )
    return cr.fetchall()


def _normalize_commercial_group_mirror(cr, rel_table, fk_col, record_id, root_id):
    """FF-73: setelah record berhasil di-resolve secara aman ke SATU root,
    pastikan compatibility mirror (rel_table -- sale_order_ids) berisi
    SELURUH commercial group (root + seluruh sale.order dengan
    original_quotation_id = root), bukan cuma anggota yang sudah ada
    sebelum migration. Idempotent: hanya INSERT baris yang belum ada,
    dan tidak pernah menambahkan quotation dari root lain."""
    cr.execute(
        f"""
        INSERT INTO {rel_table} ({fk_col}, sale_order_id)
        SELECT %s, so.id
        FROM sale_order so
        WHERE (so.id = %s OR so.original_quotation_id = %s)
          AND NOT EXISTS (
              SELECT 1 FROM {rel_table} existing
              WHERE existing.{fk_col} = %s AND existing.sale_order_id = so.id
          )
        """,
        (record_id, root_id, root_id, record_id),
    )


def _fetch_resolved_roots(cr, main_table):
    """Seluruh record main_table (Booking) yang SUDAH punya root_quotation_id
    -- baik yang baru di-resolve run migration ini maupun yang sudah terisi
    sebelumnya (produksi atau run migration sebelumnya). Dipakai sebagai basis
    normalisasi mirror Jobsheet-via-Booking, supaya idempotent: re-run
    migration tetap ikut menormalisasi variant baru yang ditambahkan ke root
    setelah run pertama, bukan cuma booking yang baru resolve run ini."""
    cr.execute(f"SELECT id, root_quotation_id FROM {main_table} WHERE root_quotation_id IS NOT NULL")
    return dict(cr.fetchall())


def _normalize_jobsheet_mirror_via_booking(cr, jobsheet_table, jobsheet_rel_table, jobsheet_fk_col, booking_roots):
    """FF-73 follow-up: Jobsheet Export yang dibuat lewat Booking (booking_id
    terisi) SENGAJA tidak punya root_quotation_id sendiri -- root-nya derived
    dari Booking (lihat FreightSeaHbl/FreightAirHawb._get_root_quotation()).
    Tapi compatibility mirror sale_order_ids-nya tetap harus dinormalisasi ke
    FULL commercial group root Booking tersebut -- sebelumnya Jobsheet dengan
    booking_id terisi dilewati SELURUHNYA oleh _backfill_and_normalize
    (extra_filter "booking_id IS NULL"), jadi mirror-nya tidak pernah
    dilengkapi sama sekali.

    root_quotation_id Jobsheet TIDAK PERNAH ditulis di sini -- hanya
    sale_order_ids (mirror) yang dinormalisasi, dan HANYA untuk Booking yang
    sudah resolve aman ke satu root (booking_roots hasil _fetch_resolved_roots
    -- Booking yang ambigu/tidak punya root tidak ada di situ, sehingga
    Jobsheet-nya otomatis tidak disentuh, TIDAK ditebak)."""
    if not booking_roots:
        return
    cr.execute(
        f"SELECT id, booking_id FROM {jobsheet_table} WHERE booking_id = ANY(%s)",
        (list(booking_roots.keys()),),
    )
    for jobsheet_id, booking_id in cr.fetchall():
        root_id = booking_roots[booking_id]
        _normalize_commercial_group_mirror(cr, jobsheet_rel_table, jobsheet_fk_col, jobsheet_id, root_id)


def _backfill_and_normalize(cr, label, main_table, rel_table, fk_col, extra_filter=""):
    rows = _fetch_candidate_roots(cr, main_table, rel_table, fk_col, extra_filter)

    resolved_count = 0
    conflicts = []
    for record_id, roots in rows:
        root_id = resolve_single_root(roots)
        if root_id is None:
            conflicts.append((record_id, sorted({r for r in roots if r is not None})))
            continue
        cr.execute(
            f"UPDATE {main_table} SET root_quotation_id = %s WHERE id = %s",
            (root_id, record_id),
        )
        _normalize_commercial_group_mirror(cr, rel_table, fk_col, record_id, root_id)
        resolved_count += 1

    for record_id, conflicting_roots in conflicts:
        _logger.warning(
            "FF-73: %s id=%s punya sale_order_ids yang resolve ke %s root berbeda "
            "(root ids: %s) -- root_quotation_id DIBIARKAN kosong, tidak ada "
            "arbitrary canonicalization (dulu: MIN(sale_order_id)).",
            label, record_id, len(conflicting_roots), conflicting_roots,
        )

    _logger.info(
        "FF-73: %s -- root_quotation_id ter-resolve aman untuk %s record, "
        "%s record dibiarkan kosong karena sale_order_ids-nya resolve ke >1 root.",
        label, resolved_count, len(conflicts),
    )


def migrate(cr, version):
    """FF-73: backfill root_quotation_id untuk Booking/HBL/HAWB yang sudah ada,
    supaya constraint commercial-group (freight.commercial.group.mixin) tidak
    langsung menolak data lama begitu record itu diedit ulang.

    Root diresolve dari SELURUH anggota sale_order_ids (bukan cuma salah satu
    yang sale_order_id-nya paling kecil seperti sebelumnya) -- tiap anggota
    dinaikkan ke root-nya sendiri lewat COALESCE(original_quotation_id, id).
    Kalau seluruh anggota resolve ke root yang SAMA, root itu yang dipakai.
    Kalau resolve ke root yang BERBEDA (data legacy yang sudah ambigu/rusak
    sebelum FF-73 ada), root_quotation_id DIBIARKAN kosong -- tidak ada
    pilihan arbitrer -- dan di-log sebagai WARNING supaya bisa ditelusuri
    manual. Kalau sale_order_ids kosong, root_quotation_id juga dibiarkan
    kosong (tidak ada dasar apa pun untuk resolve).

    Setelah root berhasil di-resolve dengan aman, compatibility mirror
    (sale_order_ids) dilengkapi supaya berisi SELURUH commercial group
    (root + seluruh currency variant-nya yang sudah ada sebelum upgrade),
    bukan cuma anggota yang sempat tercatat sebelum FF-73.

    Untuk HBL/HAWB yang punya booking_id terisi (flow Export lewat Booking),
    root_quotation_id DIBIARKAN kosong secara sengaja — root-nya didapat
    lewat Booking (lihat FreightSeaHbl/FreightAirHawb._get_root_quotation()),
    bukan disimpan dobel di Jobsheet. HARUS post-migrate: kolom
    root_quotation_id baru dibuat oleh _auto_init setelah pre-migrate.

    Migration ini idempotent: memanggilnya berkali-kali tidak mengubah hasil
    (WHERE root_quotation_id IS NULL mencegah record yang sudah ter-resolve
    diproses ulang, dan mirror INSERT memakai NOT EXISTS).

    Follow-up gap fix: Jobsheet Export lewat Booking (booking_id terisi)
    sengaja TIDAK diberi root_quotation_id sendiri (root-nya derived dari
    Booking) -- TAPI compatibility mirror sale_order_ids-nya tetap harus
    dinormalisasi ke commercial group root Booking tersebut, sama seperti
    Booking/Jobsheet direct. Lihat _normalize_jobsheet_mirror_via_booking().
    """
    # Booking (Sea & Air): backfill dari sale_order_ids
    for label, main_table, rel_table, fk_col in [
        ("freight.sea.booking", "freight_sea_booking", "freight_sea_booking_sale_order_rel", "freight_sea_booking_id"),
        ("freight.air.booking", "freight_air_booking", "freight_air_booking_sale_order_rel", "freight_air_booking_id"),
    ]:
        _backfill_and_normalize(cr, label, main_table, rel_table, fk_col)

    # Jobsheet Export lewat Booking (booking_id terisi): root_quotation_id
    # TETAP tidak disentuh (derived dari Booking), tapi mirror sale_order_ids
    # dinormalisasi ke root Booking -- generic, dipakai sama untuk Sea & Air.
    _normalize_jobsheet_mirror_via_booking(
        cr, "freight_sea_hbl", "freight_sea_hbl_sale_order_rel", "freight_sea_hbl_id",
        _fetch_resolved_roots(cr, "freight_sea_booking"),
    )
    _normalize_jobsheet_mirror_via_booking(
        cr, "freight_air_hawb", "freight_air_hawb_sale_order_rel", "freight_air_hawb_id",
        _fetch_resolved_roots(cr, "freight_air_booking"),
    )

    # HBL (Sea) & HAWB (Air): backfill HANYA yang TIDAK punya booking_id
    # (flow direct-import) -- yang punya booking_id sengaja dibiarkan kosong
    # (root_quotation_id-nya), sudah ditangani di atas untuk mirror-nya.
    for label, main_table, rel_table, fk_col in [
        ("freight.sea.hbl", "freight_sea_hbl", "freight_sea_hbl_sale_order_rel", "freight_sea_hbl_id"),
        ("freight.air.hawb", "freight_air_hawb", "freight_air_hawb_sale_order_rel", "freight_air_hawb_id"),
    ]:
        _backfill_and_normalize(cr, label, main_table, rel_table, fk_col, extra_filter="AND m.booking_id IS NULL")
