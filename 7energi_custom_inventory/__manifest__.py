# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : '7energi_custom_inventory',
    'version' : '14.0.0.6',
    'summary': '''Custom Inventory And Printouts For 7Energi''',
    'sequence': 10,
    'author': 'Garudea',
    'category': 'Inventory/Inventory',
    'depends' : ['base', 'stock', 'stock_account', '7energi_custom_sale_order'],
    'data': [
        'views/stock_picking_views.xml',
        'reports/7energi_delivery_order_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}