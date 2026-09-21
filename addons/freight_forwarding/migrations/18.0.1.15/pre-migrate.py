import logging

_logger = logging.getLogger(__name__)

# Mapping: nilai Char lama (lowercase, stripped) → value Selection baru
_CHARGE_UNIT_MAP = {
    '20ft container': '20ft',
    '20ft': '20ft',
    '20 ft container': '20ft',
    '40ft container': '40ft',
    '40ft': '40ft',
    '40 ft container': '40ft',
    '45ft container': '45ft',
    '45ft': '45ft',
    '45 ft container': '45ft',
    'total container': 'total_container',
    'total_container': 'total_container',
    'rev ton/ charge weight': 'rev_ton_cw',
    'rev ton/charge weight': 'rev_ton_cw',
    'rev ton charge weight': 'rev_ton_cw',
    'rev_ton_cw': 'rev_ton_cw',
    'rev ton rnd up': 'rev_ton_rnd',
    'rev ton rnd': 'rev_ton_rnd',
    'rev_ton_rnd': 'rev_ton_rnd',
    'shipment': 'shipment',
    'house': 'house',
}


def migrate(cr, version):
    """18.0.1.11 pre-migrate:
    1. Rename charge_code_id → product_tmpl_id in freight_charge_code_account_mapping.
    2. Migrate freight_charge_code records → product_template rows.
    3. Update account_mapping FK to point to new product_template ids.
    4. Drop freight_charge_code table.
    """
    if not _table_exists(cr, 'freight_charge_code'):
        _logger.info("freight_charge_code not found — pre-migrate skipped.")
        return

    # 1. Rename FK column in account mapping (if still old name)
    if _column_exists(cr, 'freight_charge_code_account_mapping', 'charge_code_id'):
        cr.execute("""
            ALTER TABLE freight_charge_code_account_mapping
            RENAME COLUMN charge_code_id TO product_tmpl_id
        """)
        _logger.info("Renamed charge_code_id → product_tmpl_id in account mapping table.")

    # Drop old FK constraint (now points to wrong table after rename)
    cr.execute("""
        ALTER TABLE freight_charge_code_account_mapping
        DROP CONSTRAINT IF EXISTS freight_charge_code_account_mapping_charge_code_id_fkey
    """)

    # 2. Read all freight_charge_code records
    cr.execute("""
        SELECT id, item_code, item_description, local_name, item_short_code,
               charge_type, module_code, department_code, recoverable,
               split_by_method, charge_unit, uom_id, site_code,
               sales_account_id, cost_account_id, sales_provision_account_id,
               provision_account_id, cost_center_code, sales_analysis_code,
               cost_analysis_code, billing_currency_id, vat_id, cost_vat_id,
               wht_tax_id, consolidation_item_id, locked, sales_cost_type,
               cost_amount, cost_percent, active, create_uid, write_uid,
               create_date, write_date
        FROM freight_charge_code
    """)
    rows = cr.fetchall()
    _logger.info("Migrating %s freight.charge.code records to product.template", len(rows))

    if not rows:
        _drop_old_table(cr)
        return

    # Map old charge_code.id → new product_template.id
    id_map = {}
    unmapped_units = []

    for row in rows:
        (old_id, item_code, item_description, local_name, item_short_code,
         charge_type, module_code, department_code, recoverable,
         split_by_method, charge_unit, uom_id, site_code,
         sales_account_id, cost_account_id, sales_provision_account_id,
         provision_account_id, cost_center_code, sales_analysis_code,
         cost_analysis_code, billing_currency_id, vat_id, cost_vat_id,
         wht_tax_id, _consolidation_item_id, locked, sales_cost_type,
         cost_amount, cost_percent, active, create_uid, write_uid,
         create_date, write_date) = row

        # Normalize charge_unit Char → Selection
        mapped_unit = None
        if charge_unit:
            mapped_unit = _CHARGE_UNIT_MAP.get(charge_unit.strip().lower())
            if not mapped_unit:
                unmapped_units.append((old_id, item_code, charge_unit))
                _logger.warning(
                    "charge_unit '%s' (charge_code id=%s, item_code=%s) "
                    "tidak match opsi baku — diset NULL, perlu review manual.",
                    charge_unit, old_id, item_code,
                )

        # Use item_code as product name; fallback to item_description
        product_name = item_code or item_description or f"CHARGE-{old_id}"

        cr.execute("""
            INSERT INTO product_template (
                name, type, active, is_charge_code,
                cc_item_code, cc_item_description, cc_local_name, cc_item_short_code,
                cc_charge_type, cc_module_code, cc_department_code, cc_recoverable,
                cc_split_by_method, cc_charge_unit, cc_uom_id, cc_site_code,
                cc_sales_account_id, cc_cost_account_id,
                cc_sales_provision_account_id, cc_provision_account_id,
                cc_cost_center_code, cc_sales_analysis_code, cc_cost_analysis_code,
                cc_billing_currency_id, cc_vat_id, cc_cost_vat_id, cc_wht_tax_id,
                cc_locked, cc_sales_cost_type, cc_cost_amount, cc_cost_percent,
                create_uid, write_uid, create_date, write_date
            ) VALUES (
                %s, 'service', %s, TRUE,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            )
            RETURNING id
        """, (
            product_name, active,
            item_code, item_description, local_name, item_short_code,
            charge_type, module_code, department_code, recoverable,
            split_by_method, mapped_unit, uom_id, site_code,
            sales_account_id, cost_account_id,
            sales_provision_account_id, provision_account_id,
            cost_center_code, sales_analysis_code, cost_analysis_code,
            billing_currency_id, vat_id, cost_vat_id, wht_tax_id,
            locked, sales_cost_type, cost_amount, cost_percent,
            create_uid, write_uid, create_date, write_date,
        ))
        new_id = cr.fetchone()[0]
        id_map[old_id] = new_id
        _logger.info("Migrated charge_code #%s (%s) → product_template #%s", old_id, item_code, new_id)

    # 3a. Update consolidation_item_id self-reference using id_map
    for old_id, new_id in id_map.items():
        cr.execute(
            "SELECT consolidation_item_id FROM freight_charge_code WHERE id = %s",
            (old_id,)
        )
        row = cr.fetchone()
        if row and row[0] and row[0] in id_map:
            cr.execute(
                "UPDATE product_template SET cc_consolidation_item_id = %s WHERE id = %s",
                (id_map[row[0]], new_id)
            )

    # 3b. Update account_mapping product_tmpl_id to new product_template ids
    for old_id, new_id in id_map.items():
        cr.execute(
            "UPDATE freight_charge_code_account_mapping SET product_tmpl_id = %s WHERE product_tmpl_id = %s",
            (new_id, old_id)
        )

    # 4. Drop old table
    _drop_old_table(cr)

    # Summary
    _logger.info(
        "Migration complete: %s records migrated. Unmapped charge_unit: %s",
        len(id_map), unmapped_units or "none",
    )

    # Verification query
    cr.execute("SELECT COUNT(*) FROM product_template WHERE is_charge_code = TRUE")
    count = cr.fetchone()[0]
    _logger.info("Verification: product_template WHERE is_charge_code=TRUE → %s rows", count)


def _drop_old_table(cr):
    cr.execute("DELETE FROM ir_model_data WHERE model = 'freight.charge.code'")
    cr.execute("""
        DELETE FROM ir_model_data WHERE model = 'ir.model.fields'
        AND res_id IN (SELECT id FROM ir_model_fields WHERE model_id IN (
            SELECT id FROM ir_model WHERE model = 'freight.charge.code'
        ))
    """)
    cr.execute("""
        DELETE FROM ir_model_fields WHERE model_id IN (
            SELECT id FROM ir_model WHERE model = 'freight.charge.code'
        )
    """)
    cr.execute("DELETE FROM ir_model_access WHERE model_id IN (SELECT id FROM ir_model WHERE model = 'freight.charge.code')")
    cr.execute("DELETE FROM ir_model WHERE model = 'freight.charge.code'")
    cr.execute("DROP TABLE IF EXISTS freight_charge_code CASCADE")
    _logger.info("Dropped freight_charge_code table and cleaned ir.model metadata.")


def _table_exists(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
        (table, column),
    )
    return bool(cr.fetchone())
