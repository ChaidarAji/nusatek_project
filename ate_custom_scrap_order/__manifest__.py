# -*- coding: utf-8 -*-
{
    'name': 'ATE Custom Scrap Order',
    'version': '17.0.0.16',
    'summary': 'create analytic distribution, configuration scrap limit to budget, and blocker budget on validate multi scrap button',
    'author': 'Garudea',
    'developer': "Janbaz",
    'category': 'Inventory',
    'depends': ['base','account_budget','analytic', 'account', 'stock','stock_account', 'sh_multi_scrap_order'],
    'data': [
        "views/res_company_view.xml",
        "views/stock_view.xml",
        "views/sh_scrap_order_view.xml",
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'OPL-1',
}
