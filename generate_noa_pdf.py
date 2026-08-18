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
        
        # Get the NOA report
        report = env['ir.actions.report'].search([('name', '=', 'NOA SYSFREIGHT')])
        if not report:
            print("Report not found!")
            sys.exit(1)
        
        print(f"Report found: {report.name} (ID: {report.id})")
        
        # Get first HBL record
        hbl = env['freight.sea.hbl'].search([], limit=1)
        if not hbl:
            print("No HBL records found!")
            sys.exit(1)
        
        print(f"HBL record: {hbl[0].job_no}")
        
        # Try to render the PDF
        try:
            pdf, _ = env['ir.actions.report']._render_qweb_pdf(report.id, hbl.ids)
            
            # Save to file
            output_path = '/tmp/noa_test.pdf'
            with open(output_path, 'wb') as f:
                f.write(pdf)
            
            print(f"PDF generated successfully!")
            print(f"File size: {len(pdf)} bytes")
            print(f"Output: {output_path}")
            
        except Exception as e:
            print(f"Error rendering PDF: {e}")
            import traceback
            traceback.print_exc()
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
