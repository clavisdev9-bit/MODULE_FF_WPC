import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migration 18.0.1.13 (FF-76 Step 2: integrate Sea with shared transport
    document registry):

    Backfills `freight.transport.document` (transport_mode='sea') records
    from existing `freight_sea_booking.bl_no` / `freight_sea_job.bl_no`
    values (read as legacy SOURCE only, never as a write target for new
    data), and wires the new `document_id` relation on both tables.

    Corrective pass: `bl_no` on both models is now RETIRED as canonical
    source of truth -- it is `related="document_id.document_no",
    store=True, readonly=True` (see models/sea/booking/booking.py and
    models/sea/hbl/hbl.py). This migration also force-syncs the physical
    `bl_no` column to match the linked document's `document_no` (see the
    safety-net UPDATEs near the end) so the compatibility display value
    is never lost regardless of Odoo's related-field recompute ordering
    relative to this script.

    This is a POST-migrate (not pre-migrate) because it needs the new
    `document_id` columns to already exist -- those are created by Odoo's
    own _auto_init during this same module upgrade, which runs BETWEEN
    pre-migrate and post-migrate.

    Conservative/safe-guard rules (per explicit instruction: never
    fabricate/change a B/L number, never silently merge unrelated data):
    - A `freight.transport.document` row is created/reused per DISTINCT
      bl_no string (scoped to transport_mode='sea').
    - CROSS-TABLE relationship-aware chain proof (corrective pass): two
      legacy rows sharing the exact same bl_no string are ONLY allowed to
      share the resulting document if they are PROVABLY the same
      Booking+Master chain -- i.e. a `freight_sea_booking` row B and a
      `freight_sea_job` row J where J.record_level = 'master' AND
      J.booking_id = B.id. Matching bl_no string ALONE is never sufficient
      (that was the bug this corrective pass fixes): a House sharing its
      Master's bl_no, two unrelated Bookings, two unrelated Jobs, or a
      Booking matched to a Job that is not actually its own Master must
      NEVER end up pointing at the same document row.
    - For every legacy bl_no value, all candidate rows (across BOTH
      tables) are grouped together first. If a legal Booking+Master pair
      is found within that group, only those two rows are linked to the
      document. Every other candidate in the same bl_no group (unrelated
      Booking, unrelated Job, House, etc.) is left with document_id = NULL
      and a WARNING is logged -- it is NOT silently merged and NOT
      force-migrated onto a different fabricated number.
    - If no legal chain exists in the group and there is exactly one
      candidate total, it is linked unambiguously. If there is no legal
      chain and MORE than one candidate, the conflict is unresolvable from
      relationship data alone: the lowest-id candidate (deterministic,
      not "most correct") is linked and the rest are left NULL with a
      WARNING, exactly like the same-chain case above.
    - `freight_sea_booking.document_id` and `freight_sea_job.document_id`
      are each protected by their own NEW unique constraint
      (document_id_uniq), so this algorithm never attempts to link more
      than one row per table to the same document anyway -- the grouping
      logic above is what decides WHICH row wins that slot instead of
      leaving it to raw insertion order.
    """
    _logger.info("Migration 18.0.1.13: backfilling Sea transport documents from bl_no")

    if not _column_exists(cr, "freight_sea_booking", "document_id") or not _column_exists(cr, "freight_sea_job", "document_id"):
        _logger.warning(
            "Migration 18.0.1.13: document_id column(s) not found yet on "
            "freight_sea_booking/freight_sea_job -- skipping backfill (will "
            "no-op safely; re-run module upgrade if this was unexpected)."
        )
        return

    def get_or_create_doc(bl_no):
        cr.execute(
            "SELECT id FROM freight_awb_master WHERE transport_mode = 'sea' AND document_no = %s",
            (bl_no,),
        )
        row = cr.fetchone()
        if row:
            return row[0]
        cr.execute(
            "INSERT INTO freight_awb_master "
            "(document_no, transport_mode, is_used, create_uid, create_date, write_uid, write_date) "
            "VALUES (%s, 'sea', false, 1, NOW(), 1, NOW()) RETURNING id",
            (bl_no,),
        )
        return cr.fetchone()[0]

    # -- Load ALL legacy candidates (both tables) up front, grouped by
    #    bl_no, so cross-table legality can be decided per group BEFORE
    #    anything gets linked (see algorithm in the docstring above).
    cr.execute(
        "SELECT id, bl_no FROM freight_sea_booking "
        "WHERE bl_no IS NOT NULL AND bl_no != '' AND document_id IS NULL "
        "ORDER BY id"
    )
    booking_rows = cr.fetchall()

    cr.execute(
        "SELECT id, bl_no, record_level, booking_id FROM freight_sea_job "
        "WHERE bl_no IS NOT NULL AND bl_no != '' AND document_id IS NULL "
        "ORDER BY id"
    )
    job_rows = cr.fetchall()

    groups = {}
    for booking_id, bl_no in booking_rows:
        groups.setdefault(bl_no, {"bookings": [], "jobs": []})["bookings"].append(booking_id)
    for job_id, bl_no, record_level, job_booking_id in job_rows:
        groups.setdefault(bl_no, {"bookings": [], "jobs": []})["jobs"].append(
            (job_id, record_level, job_booking_id)
        )

    for bl_no, members in groups.items():
        booking_ids = members["bookings"]
        jobs = members["jobs"]

        # Relationship-aware chain proof: a booking B and a job J may
        # share the document ONLY if J is provably B's own Master
        # (record_level='master' AND J.booking_id == B.id) -- NOT merely
        # because they happen to carry the same bl_no string.
        winners_booking = set()
        winners_job = set()
        legal_chain_found = False
        for job_id, record_level, job_booking_id in jobs:
            if record_level == "master" and job_booking_id in booking_ids:
                winners_booking.add(job_booking_id)
                winners_job.add(job_id)
                legal_chain_found = True
                break  # one legal chain claims this bl_no; anything else
                       # left in the group below is a genuine conflict.

        if not legal_chain_found:
            candidates = [("booking", bid) for bid in booking_ids] + [
                ("job", jid) for jid, _rl, _bid in jobs
            ]
            if len(candidates) == 1:
                kind, cid = candidates[0]
                (winners_booking if kind == "booking" else winners_job).add(cid)
            elif len(candidates) > 1:
                # No provable relationship -- deterministic conservative
                # pick (lowest id), NOT a "best guess": everything else
                # in the group stays unlinked and gets a warning below.
                candidates.sort(key=lambda c: c[1])
                kind, cid = candidates[0]
                (winners_booking if kind == "booking" else winners_job).add(cid)

        doc_id = None
        if winners_booking or winners_job:
            doc_id = get_or_create_doc(bl_no)

        for booking_id in booking_ids:
            if booking_id in winners_booking:
                cr.execute(
                    "UPDATE freight_sea_booking SET document_id = %s WHERE id = %s",
                    (doc_id, booking_id),
                )
            else:
                _logger.warning(
                    "Migration 18.0.1.13: freight_sea_booking id=%s has bl_no=%r "
                    "which conflicts with another unrelated Booking/Job also "
                    "claiming the same B/L (no provable same-chain "
                    "relationship) -- leaving document_id NULL for manual "
                    "review (bl_no NOT changed).",
                    booking_id, bl_no,
                )

        for job_id, record_level, job_booking_id in jobs:
            if job_id in winners_job:
                cr.execute(
                    "UPDATE freight_sea_job SET document_id = %s WHERE id = %s",
                    (doc_id, job_id),
                )
            else:
                _logger.warning(
                    "Migration 18.0.1.13: freight_sea_job id=%s (record_level=%s) "
                    "has bl_no=%r which conflicts with another unrelated "
                    "Booking/Job also claiming the same B/L (no provable "
                    "same-chain relationship) -- leaving document_id NULL for "
                    "manual review (bl_no NOT changed).",
                    job_id, record_level, bl_no,
                )

    # -- Historical usage bookkeeping (is_used + pointer) -----------------
    cr.execute(
        "UPDATE freight_awb_master d SET is_used = true, used_sea_booking_id = b.id "
        "FROM freight_sea_booking b WHERE b.document_id = d.id AND d.is_used = false"
    )
    cr.execute(
        "UPDATE freight_awb_master d SET is_used = true, used_sea_job_id = j.id "
        "FROM freight_sea_job j WHERE j.document_id = d.id AND d.is_used = false "
        "AND d.used_sea_booking_id IS NULL"
    )

    # -- bl_no physical column safety-net (corrective pass) --------------
    # `bl_no` is now `related="document_id.document_no", store=True` on
    # both models. Odoo's own schema-sync step (which runs BEFORE this
    # post-migrate, right after pre-migrate) may already have recomputed
    # the stored related field while `document_id` was still NULL for
    # every legacy row -- which would blank out the physical `bl_no`
    # column. Our raw-SQL UPDATE above to `document_id` does NOT go
    # through the ORM, so it does not itself trigger Odoo's related-field
    # recompute either. Force the physical column back in sync directly
    # so the compatibility display value is never lost, regardless of
    # exact recompute ordering.
    cr.execute(
        "UPDATE freight_sea_booking b SET bl_no = d.document_no "
        "FROM freight_awb_master d WHERE b.document_id = d.id "
        "AND (b.bl_no IS DISTINCT FROM d.document_no)"
    )
    cr.execute(
        "UPDATE freight_sea_job j SET bl_no = d.document_no "
        "FROM freight_awb_master d WHERE j.document_id = d.id "
        "AND (j.bl_no IS DISTINCT FROM d.document_no)"
    )

    _logger.info("Migration 18.0.1.13: Sea transport document backfill complete.")


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cr.fetchone() is not None
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Replace the stored display field with the native Product name."""
    cr.execute("""
        UPDATE product_template
        SET name = jsonb_build_object('en_US', CASE
            WHEN NULLIF(BTRIM(cc_item_code), '') IS NOT NULL
                 AND NULLIF(BTRIM(cc_item_description), '') IS NOT NULL
                THEN BTRIM(cc_item_code) || ' - ' || BTRIM(cc_item_description)
            WHEN NULLIF(BTRIM(cc_item_code), '') IS NOT NULL
                THEN BTRIM(cc_item_code)
            WHEN NULLIF(BTRIM(cc_item_description), '') IS NOT NULL
                THEN BTRIM(cc_item_description)
            ELSE COALESCE(name->>'en_US', '')
        END)
        WHERE is_charge_code = TRUE
    """)
    updated = cr.rowcount
    _logger.info('Updated native name for %s Charge Code products.', updated)

    cr.execute("""
        SELECT id, name, cc_item_code, cc_item_description
        FROM product_template
        WHERE is_charge_code = TRUE
        ORDER BY id
        LIMIT 5
    """)
    _logger.info('Charge Code name sample after migration: %s', cr.fetchall())

    cr.execute("""
        ALTER TABLE product_template
        DROP COLUMN IF EXISTS cc_display_name
    """)
    _logger.info('Removed legacy product_template.cc_display_name column if present.')