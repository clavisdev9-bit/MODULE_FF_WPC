import logging

_logger = logging.getLogger(__name__)

CATEGORY_MAP = [
    ('uom_category_freight', 'Freight'),
    ('uom_category_fcl', 'FCL'),
    ('uom_category_container', 'Container'),
    ('uom_category_air', 'Air'),
    ('uom_category_trucking', 'Trucking'),
    ('uom_category_warehouse', 'Warehouse'),
    ('uom_category_documentation', 'Documentation'),
    ('uom_category_sea', 'Sea'),
    ('uom_category_customs', 'Customs'),
    ('uom_category_general', 'General'),
]

UOM_MAP = [
    ('uom_freight_kg', 'KG'),
    ('uom_freight_kgs', 'KGS'),
    ('uom_freight_cbm', 'CBM'),
    ('uom_freight_m3', 'M3'),
    ('uom_freight_w_m', 'W/M'),
    ('uom_freight_rt', 'RT'),
    ('uom_freight_ton', 'Ton'),
    ('uom_fcl_20ft', '20FT'),
    ('uom_fcl_40ft', '40FT'),
    ('uom_fcl_40hc', '40HC'),
    ('uom_fcl_45hc', '45HC'),
    ('uom_container_container', 'Container'),
    ('uom_air_awb', 'AWB'),
    ('uom_air_hawb', 'HAWB'),
    ('uom_air_mawb', 'MAWB'),
    ('uom_air_shipment', 'Shipment'),
    ('uom_trucking_trip', 'Trip'),
    ('uom_trucking_truck', 'Truck'),
    ('uom_trucking_unit', 'Unit'),
    ('uom_trucking_day', 'Day'),
    ('uom_trucking_hour', 'Hour'),
    ('uom_trucking_km', 'KM'),
    ('uom_warehouse_pallet', 'Pallet'),
    ('uom_warehouse_carton', 'Carton'),
    ('uom_warehouse_ctn', 'CTN'),
    ('uom_warehouse_package', 'Package'),
    ('uom_warehouse_pkg', 'PKG'),
    ('uom_warehouse_day', 'Day'),
    ('uom_warehouse_month', 'Month'),
    ('uom_documentation_shipment', 'Shipment'),
    ('uom_documentation_job', 'Job'),
    ('uom_documentation_set', 'Set'),
    ('uom_documentation_doc', 'DOC'),
    ('uom_sea_bl', 'BL'),
    ('uom_sea_hbl', 'HBL'),
    ('uom_sea_mbl', 'MBL'),
    ('uom_customs_shipment', 'Shipment'),
    ('uom_customs_job', 'Job'),
    ('uom_customs_document', 'Document'),
    ('uom_customs_declaration', 'Declaration'),
    ('uom_customs_entry', 'Entry'),
    ('uom_general_pcs', 'PCS'),
    ('uom_general_lot', 'Lot'),
    ('uom_general_service', 'Service'),
    ('uom_general_lump_sum', 'Lump Sum'),
]


def migrate(cr, version):
    """
    Migration 18.0.1.2 (FF-57):
    1. Reset noupdate flag on ir_model_data for freight_forwarding UOM records.
    2. Direct database update of UOM category and unit names:
       - Acronyms (FCL, KG, CBM, AWB, BL, etc.) in FULL UPPERCASE
       - General words (Freight, Container, Shipment, Day, etc.) in Title Case
    """
    _logger.info("Migration 18.0.1.2: resetting noupdate on freight_forwarding UOM records...")
    cr.execute("""
        UPDATE ir_model_data
        SET noupdate = false
        WHERE module = 'freight_forwarding'
          AND (name LIKE 'uom_category_%' OR name LIKE 'uom_%');
    """)

    _update_names(cr, 'uom_category', 'uom.category', CATEGORY_MAP)
    _update_names(cr, 'uom_uom', 'uom.uom', UOM_MAP)
    _logger.info("Migration 18.0.1.2: UOM names updated successfully.")


def _update_names(cr, table, model, mapping):
    cr.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = 'name'
    """, (table,))
    row = cr.fetchone()
    if not row:
        return
    col_type = row[0].lower()
    is_json = 'json' in col_type

    for xml_name, new_name in mapping:
        if is_json:
            cr.execute(f"""
                UPDATE {table} t
                SET name = jsonb_set(
                    CASE WHEN jsonb_typeof(t.name) = 'object' THEN t.name ELSE '{{}}'::jsonb END,
                    '{{en_US}}',
                    to_jsonb(%s::text)
                )
                FROM ir_model_data imd
                WHERE imd.module = 'freight_forwarding'
                  AND imd.name = %s
                  AND imd.model = %s
                  AND imd.res_id = t.id
            """, (new_name, xml_name, model))
        else:
            cr.execute(f"""
                UPDATE {table} t
                SET name = %s
                FROM ir_model_data imd
                WHERE imd.module = 'freight_forwarding'
                  AND imd.name = %s
                  AND imd.model = %s
                  AND imd.res_id = t.id
            """, (new_name, xml_name, model))
