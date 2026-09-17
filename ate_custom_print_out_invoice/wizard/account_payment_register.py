# -*- coding: utf-8 -*-
from odoo import models,fields

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _get_total_amount_in_wizard_currency_to_full_reconcile(self, batch_result, early_payment_discount=True):
        for wizard in self:
            amount, discount = super()._get_total_amount_in_wizard_currency_to_full_reconcile(batch_result, early_payment_discount)
            source_curr = wizard.source_currency_id  # invoice currency
            wizard_curr = wizard.currency_id  # journal currency
            if (source_curr and wizard_curr and source_curr != wizard_curr):
                amount = wizard_curr._convert(
                    wizard.source_amount_currency,
                    source_curr,
                    wizard.company_id,
                    wizard.payment_date or fields.Date.today(),
                    round=False,
                )

        return amount, discount

