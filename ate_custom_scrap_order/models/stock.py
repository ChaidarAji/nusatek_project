# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_multi_scrap_order(self):
        """Return the multi scrap order being validated (from context), or an empty recordset."""
        scrap_id = self.env.context.get('scrap_id')
        if self.env.context.get('is_scrap') and scrap_id:
            return self.env['sh.scrap.order'].browse(scrap_id).exists()
        return self.env['sh.scrap.order']

    def _get_multi_scrap_analytic_distribution(self, scrap_order):
        if scrap_order and scrap_order.account_analytic_id:
            return {str(scrap_order.account_analytic_id.id): 100.0}
        return False

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id,
                                   cost):
        result = super(StockMove, self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty,
                                                                   description, svl_id, cost)
        if self.env.context.get('is_scrap'):
            scrap_order = self._get_multi_scrap_order()
            result.update({
                # header Analytic Account (ate_custom_invoice_bill) and Analytic Distribution (globle_analytic_distribution)
                'analytic_account_id': scrap_order.account_analytic_id.id or False,
                'analytic_distribution': self._get_multi_scrap_analytic_distribution(scrap_order),
            })

        return result

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id,
                                       credit_account_id, svl_id, description):
        result = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value,
                                                                       debit_account_id, credit_account_id, svl_id,
                                                                       description)
        if self.env.context.get('is_scrap'):
            scrap_order = self._get_multi_scrap_order()
            analytic_distribution = self._get_multi_scrap_analytic_distribution(scrap_order)
            stock_valuation_account_outgoing = debit_account_id

            for line in scrap_order.sh_scrap_order_line:
                if line.product_id.id == result['debit_line_vals']['product_id']:
                    stock_valuation_account_outgoing = line.sh_scrap_location_id.valuation_out_account_id.id

            for res in result:
                result[res].update({'analytic_distribution': analytic_distribution})

            result['debit_line_vals']['account_id'] = stock_valuation_account_outgoing

        return result
