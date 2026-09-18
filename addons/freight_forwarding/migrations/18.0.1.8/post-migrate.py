import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """FF-73: backfill root_quotation_id untuk Booking/HBL/HAWB yang sudah ada,
    supaya constraint commercial-group (freight.commercial.group.mixin) tidak
    langsung menolak data lama begitu record itu diedit ulang.

    Root diresolve dari SALAH SATU anggota sale_order_ids yang sudah ada
    (yang sale_order_id-nya paling kecil, sekadar supaya deterministik --
    tabel relasi m2m auto-generated Odoo tidak punya kolom id sendiri, cuma
    dua kolom FK), lalu dinaikkan ke root-nya sendiri (original_quotation_id
    kalau quotation itu sendiri adalah currency variant).

    Untuk HBL/HAWB yang punya booking_id terisi (flow Export lewat Booking),
    root_quotation_id DIBIARKAN kosong secara sengaja — root-nya didapat
    lewat Booking (lihat FreightSeaHbl/FreightAirHawb._get_root_quotation()),
    bukan disimpan dobel di Jobsheet. HARUS post-migrate: kolom
    root_quotation_id baru dibuat oleh _auto_init setelah pre-migrate.
    """
    # Booking (Sea & Air): backfill dari sale_order_ids
    for booking_table, rel_table, booking_col in [
        ("freight_sea_booking", "freight_sea_booking_sale_order_rel", "freight_sea_booking_id"),
        ("freight_air_booking", "freight_air_booking_sale_order_rel", "freight_air_booking_id"),
    ]:
        cr.execute(
            f"""
            UPDATE {booking_table} b
            SET root_quotation_id = COALESCE(so.original_quotation_id, so.id)
            FROM {rel_table} rel
            JOIN sale_order so ON so.id = rel.sale_order_id
            WHERE b.root_quotation_id IS NULL
              AND rel.{booking_col} = b.id
              AND rel.sale_order_id = (
                  SELECT MIN(rel2.sale_order_id) FROM {rel_table} rel2 WHERE rel2.{booking_col} = b.id
              )
            """
        )
        _logger.info("FF-73: backfilled root_quotation_id for %s rows in %s", cr.rowcount, booking_table)

    # HBL (Sea) & HAWB (Air): backfill HANYA yang TIDAK punya booking_id
    # (flow direct-import) -- yang punya booking_id sengaja dibiarkan kosong.
    for jobsheet_table, rel_table, jobsheet_col in [
        ("freight_sea_hbl", "freight_sea_hbl_sale_order_rel", "freight_sea_hbl_id"),
        ("freight_air_hawb", "freight_air_hawb_sale_order_rel", "freight_air_hawb_id"),
    ]:
        cr.execute(
            f"""
            UPDATE {jobsheet_table} j
            SET root_quotation_id = COALESCE(so.original_quotation_id, so.id)
            FROM {rel_table} rel
            JOIN sale_order so ON so.id = rel.sale_order_id
            WHERE j.root_quotation_id IS NULL
              AND j.booking_id IS NULL
              AND rel.{jobsheet_col} = j.id
              AND rel.sale_order_id = (
                  SELECT MIN(rel2.sale_order_id) FROM {rel_table} rel2 WHERE rel2.{jobsheet_col} = j.id
              )
            """
        )
        _logger.info("FF-73: backfilled root_quotation_id for %s direct-import rows in %s", cr.rowcount, jobsheet_table)
