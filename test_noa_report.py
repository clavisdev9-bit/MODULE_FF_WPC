import os
import sys
os.environ['ODOO_RC'] = '/etc/odoo/odoo.conf'

import odoo
from odoo.api import Environment
from odoo.tools import config

# Configure Odoo
config.set_key('test_file', True)
config.set_key('db_name', 'odoo')
config.set_key('workers', 0)

# Start Odoo
registry = odoo.registry('odoo')

# Get the environment
with registry.cursor() as cr:
    env = Environment(cr, 2, {})
    
    # Search for NOA report
    report = env['ir.actions.report'].search([('name', 'ilike', 'NOA')])
    print(f"Found reports: {report}")
    
    # Try to find an HBL record
    hbl = env['freight.sea.hbl'].search([], limit=1)
    if hbl:
        print(f"Found HBL: {hbl.name}")
        # Try to generate the report
        try:
            html, mimetype = env['ir.actions.report']._render_qweb_pdf(
                report.id, hbl.ids
            )
            print(f"Report generated successfully, size: {len(html)} bytes")
        except Exception as e:
            print(f"Error generating report: {e}")
    else:
        print("No HBL records found")
