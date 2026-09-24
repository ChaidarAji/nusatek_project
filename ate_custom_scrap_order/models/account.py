from odoo import models, fields, api, _
from odoo.exceptions import UserError


# class CrossoveredBudgetLines(models.Model):
#     _inherit = "crossovered.budget.lines"
#
#     practical_amount = fields.Monetary(string="Practical Amount", store=True)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        for move in self:
            if self.env.context.get('is_scrap'):
                if move.move_type == 'entry':
                    for line in move.line_ids:
                        if line.account_type == 'expense' or line.account_type == 'expense_direct_cost':
                            analytic_distribution = line.analytic_distribution
                            if analytic_distribution:
                                for account_id, distribution in analytic_distribution.items():
                                    analytic_account_id = self.env['account.analytic.account'].search([('id', '=', int(account_id))], limit=1)
                                    if analytic_account_id:
                                        if analytic_account_id.crossovered_budget_line:
                                            for budget_line in analytic_account_id.crossovered_budget_line:
                                                if budget_line.crossovered_budget_state not in ['draft', 'done']:
                                                    if budget_line.date_from <= fields.Datetime.now().date() and budget_line.date_to >= fields.Datetime.now().date():
                                                        new_practical_amount = 0.0
                                                        if line.account_id in budget_line.general_budget_id.account_ids:
                                                            current_practical = budget_line.practical_amount
                                                            planned_amount = budget_line.planned_amount
                                                            if line.debit > 0 and line.credit == 0:
                                                                # This is a debit line
                                                                new_practical_amount = float(current_practical) + float(line.debit)

                                                            elif line.credit > 0 and line.debit == 0:
                                                                # This is a credit line
                                                                new_practical_amount = float(current_practical) - float(line.credit)

                                                            if move.company_id.is_scrap_limit_to_budget:
                                                                # Calculation based on planned amount
                                                                if new_practical_amount > planned_amount:
                                                                    raise UserError("Total Biaya Melebihi Budget")
                                                                else:
                                                                    budget_line.sudo().write(
                                                                        {'practical_amount': new_practical_amount})

                                                            else:
                                                                # Update budget with practical amount and check if it's still within limits
                                                                budget_line.sudo().write({'practical_amount': new_practical_amount})


        return super(AccountMove, self)._post(soft)
