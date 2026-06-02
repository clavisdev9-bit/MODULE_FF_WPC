# -*- encoding: UTF-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2015-Today Laxicon Solution.
#    (<http://laxicon.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################


{
    'name': "Japan - City Data",
    'summary': 'City Data',
    'author': "Laxicon Solution",
    'website': "www.laxicon.in",
    'sequence': 101,
    'support': 'info@laxicon.in',
    'category': 'Accounting/Localizations',
    'version': '18.0',
    'license': 'LGPL-3',
    'description': "City Data",
    'depends': ['base_address_extended'],
    'data': [
        "data/japan.xml",
        'data/res_country_data_enforce.xml'],
    'images':  ["static/description/banner.png"],
    'installable': True,
    'auto_install': False,
    'application': True,
    'pre_init_hook':  'pre_init_check'}
