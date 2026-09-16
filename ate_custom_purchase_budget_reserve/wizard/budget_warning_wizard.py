from odoo import models, fields

class BudgetWarninfWizard(models.TransientModel):
    _name = "budget.warning.wizard"


    non_listed_account = fields.Char(string="Non Listed Account for:")
    non_listed_budgetary_position = fields.Char(string="Budgetary Position is not registered in budget data for:")
    insufficient_budget_list = fields.Char(string="Insufficient Budget for:")