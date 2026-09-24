# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Company(models.Model):
    _inherit = "res.company"

    is_scrap_limit_to_budget = fields.Boolean(string="Scrap Limit To Budget")
