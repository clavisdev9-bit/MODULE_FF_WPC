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
        report = env['ir.actions.report'].search([('name', 'ilike', 'NOA')])
        print(f'Report found: {len(report)}')
        if report:
            print(f'  Name: {report[0].name}')
            print(f'  ID: {report[0].id}')
        
        # Check for HBL records
        hbl_count = env['freight.sea.hbl'].search_count([])
        print(f'HBL records: {hbl_count}')
        
        if hbl_count > 0:
            hbl = env['freight.sea.hbl'].search([], limit=1)
            print(f'  Job No: {hbl[0].job_no}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
