from odoo import models, fields, api

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    component_valuation_percentage = fields.Float(string="Component Valuation Percentage", required=True, default=0)