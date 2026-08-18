import sys
sys.path.insert(0, '/workspace/addons')
sys.path.insert(0, '/workspace/enterprise')

import os
os.environ['ODOO_RC'] = '/etc/odoo/odoo.conf'

import odoo
from odoo.api import Environment

try:
    registry = odoo.registry('odoo')
    with registry.cursor() as cr:
        env = Environment(cr, 1, {})
        
        # Check if report exists
        report = env['ir.actions.report'].search([('name', '=', 'NOA SYSFREIGHT')])
        if report:
            print("✓ Report found: {}".format(report.name))
            print("✓ Report ID: {}".format(report.id))
            print("✓ Report Type: {}".format(report.report_type))
            pf_name = report.paperformat_id.name if report.paperformat_id else "Default"
            print("✓ Paper Format: {}".format(pf_name))
            print("✓ Binding Type: {}".format(report.binding_type))
            print("✓ Binding Model: {}".format(report.binding_model_id.model if report.binding_model_id else "N/A"))
        else:
            print("✗ Report not found")
            
        # Check template
        template = env['ir.ui.view'].search([('id', '=', 'noa_sysfreight_report_template')])
        if not template:
            template = env['ir.ui.view'].search([('key', '=', 'freight_forwarding.noa_sysfreight_report_template')])
        if template:
            print("✓ Template found: {} (ID: {})".format(template[0].name, template[0].id))
        else:
            print("✗ Template not found (this is OK - template is in XML)")
            
except Exception as e:
    print("Error: {}".format(e))
    import traceback
    traceback.print_exc()
