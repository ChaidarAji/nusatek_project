# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_scrap_limit_to_budget = fields.Boolean(string="Scrap Limit To Budget")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        is_scrap_limit_to_budget = params.get_param('is_scrap_limit_to_budget', default=False)
        res.update(
            is_scrap_limit_to_budget=is_scrap_limit_to_budget,
        )
        return res

    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param("is_scrap_limit_to_budget", self.is_scrap_limit_to_budget)
        super(ResConfigSettings, self).set_values()
