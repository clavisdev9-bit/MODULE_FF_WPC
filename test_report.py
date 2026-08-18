#!/usr/bin/env python
import sys
import os
os.chdir('/workspace')
sys.path.insert(0, '/workspace')

import odoo
from odoo import api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

# Initialize Odoo environment
odoo.cli.main(['--addons-path', '/workspace/addons:/workspace/enterprise', 
               '-d', 'odoo', '--no-http', '-c', '/etc/odoo/odoo.conf', 
               'shell'])
