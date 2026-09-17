# -*- coding: utf-8 -*-

{
    "name": "Budget Customization",
    "version": "17.0.1.6",
    "summary": "Manage budget reservation from purchase transaction",
    'author': 'Garudea',
    'developer': "Vadivel Duraisamy UcaSam_dev",
    "category": "Purchase",
    "depends": ['base', 'purchase', 'purchase_stock', 'account_accountant', 'analytic', 'account_budget',
                'ate_custom_budget_module', 'globle_analytic_distribution', 'stock'],
    "data": [
        "security/ir.model.access.csv",
        "wizard/budget_warning_wizard.xml",
        "views/purchase_order.xml",
        # "views/stock_picking.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
    'license': 'OPL-1',
}
