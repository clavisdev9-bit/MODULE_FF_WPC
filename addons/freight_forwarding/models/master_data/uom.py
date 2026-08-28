from odoo import models, api


class UoM(models.Model):
    _inherit = "uom.uom"

    @api.model
    def _register_hook(self):
        super()._register_hook()
        self._sync_freight_uom_names()

    @api.model
    def _sync_freight_uom_names(self):
        """Syncs freight forwarding UOM categories and units to Capitalized Initial format."""
        try:
            self.env.cr.execute("""
                UPDATE ir_model_data
                SET noupdate = false
                WHERE module = 'freight_forwarding'
                  AND (name LIKE 'uom_category_%' OR name LIKE 'uom_%');
            """)
        except Exception:
            pass

        uom_map = {
            # Categories
            'uom_category_freight': 'Freight',
            'uom_category_fcl': 'Fcl',
            'uom_category_container': 'Container',
            'uom_category_air': 'Air',
            'uom_category_trucking': 'Trucking',
            'uom_category_warehouse': 'Warehouse',
            'uom_category_documentation': 'Documentation',
            'uom_category_sea': 'Sea',
            'uom_category_customs': 'Customs',
            'uom_category_general': 'General',
            # Units
            'uom_freight_kg': 'Kg',
            'uom_freight_kgs': 'Kgs',
            'uom_freight_cbm': 'Cbm',
            'uom_freight_m3': 'M3',
            'uom_freight_w_m': 'W/m',
            'uom_freight_rt': 'Rt',
            'uom_freight_ton': 'Ton',
            'uom_fcl_20ft': '20ft',
            'uom_fcl_40ft': '40ft',
            'uom_fcl_40hc': '40hc',
            'uom_fcl_45hc': '45hc',
            'uom_container_container': 'Container',
            'uom_air_awb': 'Awb',
            'uom_air_hawb': 'Hawb',
            'uom_air_mawb': 'Mawb',
            'uom_air_shipment': 'Shipment',
            'uom_trucking_trip': 'Trip',
            'uom_trucking_truck': 'Truck',
            'uom_trucking_unit': 'Unit',
            'uom_trucking_day': 'Day',
            'uom_trucking_hour': 'Hour',
            'uom_trucking_km': 'Km',
            'uom_warehouse_pallet': 'Pallet',
            'uom_warehouse_carton': 'Carton',
            'uom_warehouse_ctn': 'Ctn',
            'uom_warehouse_package': 'Package',
            'uom_warehouse_pkg': 'Pkg',
            'uom_warehouse_day': 'Day',
            'uom_warehouse_month': 'Month',
            'uom_documentation_shipment': 'Shipment',
            'uom_documentation_job': 'Job',
            'uom_documentation_set': 'Set',
            'uom_documentation_doc': 'Doc',
            'uom_sea_bl': 'Bl',
            'uom_sea_hbl': 'Hbl',
            'uom_sea_mbl': 'Mbl',
            'uom_customs_shipment': 'Shipment',
            'uom_customs_job': 'Job',
            'uom_customs_document': 'Document',
            'uom_customs_declaration': 'Declaration',
            'uom_customs_entry': 'Entry',
            'uom_general_pcs': 'Pcs',
            'uom_general_lot': 'Lot',
            'uom_general_service': 'Service',
            'uom_general_lump_sum': 'Lump sum',
        }

        for xml_id_suffix, expected_name in uom_map.items():
            try:
                rec = self.env.ref(f'freight_forwarding.{xml_id_suffix}', raise_if_not_found=False)
                if rec and rec.name != expected_name:
                    rec.write({'name': expected_name})
            except Exception:
                pass
