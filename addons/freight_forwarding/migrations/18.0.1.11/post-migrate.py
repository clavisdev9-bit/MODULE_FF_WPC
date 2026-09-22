import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cr.fetchone() is not None


def migrate(cr, version):
    """FF-75 catch-up: backfill `record_level` (new required field on
    freight.sea.job, see models/sea/hbl/hbl.py) for every pre-existing Sea
    Job row. Pre-FF-75 there was no Master/House concept at all -- every
    legacy row stood on its own (no master_job_id), which is structurally
    'master' (a root with no parent), not 'house' (implies joined under
    another Master) -- Odoo's own _auto_init would otherwise leave them at
    the field's bare default ('house'), which misrepresents standalone
    legacy Jobs as House cargo of some Master that never existed.

    Must be POST-migrate: `record_level` is a brand-new column, only
    created by Odoo's own schema sync that runs between pre-migrate and
    post-migrate.
    """
    if not _column_exists(cr, "freight_sea_job", "record_level"):
        _logger.warning(
            "Migration 18.0.1.11 post: freight_sea_job.record_level not "
            "found -- skipping backfill (will no-op safely; re-run module "
            "upgrade if this was unexpected)."
        )
        return

    cr.execute("UPDATE freight_sea_job SET record_level = 'master'")
    _logger.info("FF-75 catch-up: backfilled record_level='master' for all pre-existing Sea Job rows.")
