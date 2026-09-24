# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = "stock.move"

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,
                                   cost):
        result = super(StockMove, self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty,
                                                                   description, svl_id, cost)
        analytic_distribution = False
        if self.env.context.get('is_scrap'):
            if self.env.context.get('scrap_id'):
                scarp_id = self.env['sh.scrap.order'].browse(self.env.context.get('scrap_id'))
                if scarp_id:
                    # analytic_distribution = scarp_id.analytic_distribution
                    analytic_distribution = {str(scarp_id.account_analytic_id.id): 100.0}

            result.update({'analytic_distribution': analytic_distribution})

        return result

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id,
                                       credit_account_id, svl_id, description):
        result = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value,
                                                                       debit_account_id, credit_account_id, svl_id,
                                                                       description)
        analytic_distribution = False
        stock_valuation_account_outgoing = debit_account_id
        if self.env.context.get('is_scrap'):
            if self.env.context.get('scrap_id'):
                scarp_id = self.env['sh.scrap.order'].browse(self.env.context.get('scrap_id'))
                if scarp_id:
                    # analytic_distribution = scarp_id.analytic_distribution
                    analytic_distribution = {str(scarp_id.account_analytic_id.id): 100.0}

                    if scarp_id.sh_scrap_order_line:
                        for line in scarp_id.sh_scrap_order_line:
                            if line.product_id.id == result['debit_line_vals']['product_id']:
                                stock_valuation_account_outgoing = line.sh_scrap_location_id.valuation_out_account_id.id

            for res in result:
                result[res].update({'analytic_distribution': analytic_distribution})

            result['debit_line_vals']['account_id'] = stock_valuation_account_outgoing

        return result
