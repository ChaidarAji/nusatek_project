# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ScrapOrder(models.Model):
    _name = "sh.scrap.order"
    _inherit = ['analytic.mixin', 'sh.scrap.order']

    analytic_distribution = fields.Json('Analytic Distribution', compute="_compute_analytic_distribution", store=True,
                                        copy=True)

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    def update_analytic_distribution(self):
        for line in self.sh_scrap_order_line:
            line.analytic_distribution = {str(self.account_analytic_id.id): 100.0}

    def sh_action_validate(self):
        self = self.with_context(scrap_id=self.id)
        res = super(ScrapOrder, self).sh_action_validate()
        self.update_analytic_distribution()
        for sh in self.sh_scrap_order_line:
            if sh.analytic_distribution != {str(self.account_analytic_id.id): 100.0}:
                raise UserError("Analytic Distribution Harus Sama")

        return res


class ScrapOrderLine(models.Model):
    _name = 'sh.scrap.order.line'
    _inherit = ['analytic.mixin', 'sh.scrap.order.line']

