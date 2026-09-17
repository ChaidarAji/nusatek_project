# -*- coding: utf-8 -*-
{
    'name': 'ATE Custom Print Out Invoice',
    'version': '17.0.0.16',
    'author': 'Garudea',
    'developer': 'Janbaz',
    'category': 'Accounting',
    'summary': 'Invoice Print',
    "depends": ['base', 'account', 'account_accountant', 'l10n_id_efaktur', 'ate_custom_so_form', 'stock','purchase','purchase_stock'],
    "data": [
        'views/account_move_view.xml',
        'views/res_company_view.xml',
        'views/purchase_order_view.xml',
        'reports/inherit_invoice_report.xml',
        'reports/report_account_move.xml',
        'reports/reports.xml',
    ],
    "application": True,
    "installable": True,
    "license": "AGPL-3",
}
