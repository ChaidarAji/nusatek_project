# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'gsi_od14_kit_component_valuation',
    'version' : '14.0.0.12',
    'summary': '''Calculate the kit component valuation for manufactured products in Odoo 14''',
    'sequence': 10,
    'author': 'Garudea',
    'category': 'Accounting/Accounting',
    'depends' : ['base', 'mrp', 'stock', 'sale_stock'],
    'data': [
        'views/mrp_bom_views.xml',
        'views/stock_picking_views.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
