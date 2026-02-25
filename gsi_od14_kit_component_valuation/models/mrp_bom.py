# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.translate import _

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    cost_currency_id = fields.Many2one("res.currency", related="product_tmpl_id.cost_currency_id")
    cost = fields.Monetary(string="Cost", currency_field='cost_currency_id')

    @api.onchange("product_tmpl_id")
    def onchange_product_cost(self):
        self.ensure_one()
        if self.product_tmpl_id:
            self.cost = self.product_tmpl_id.standard_price
        else:
            self.cost = 0


    def kit_component_valuation_validation(self):
        """
        “Kit Component Valuation Validation” logic

        1) Collect component names where Component Valuation Percentage is negative
           -> stop save and raise warning listing those components
        2) Sum all Component Valuation Percentage
           -> if total > 100 stop save and raise warning
        """
        for bom in self:
            negative_components = []
            total = 0.0

            # If you only want this validation for kit/phantom BoM, uncomment:
            # if bom.type != 'phantom':
            #     continue

            for line in bom.bom_line_ids:
                pct = line.component_valuation_percentage or 0.0
                total += pct

                # Check negative
                if float_compare(pct, 0.0, precision_digits=6) < 0:
                    product = line.product_id
                    # Format: [default_code] Name
                    if product and product.default_code:
                        label = "[%s] %s" % (product.default_code, product.name)
                    else:
                        label = product.name if product else _("(No Component)")
                    negative_components.append(label)

            # Rule #2: after last line checked, block save if any negatives
            if negative_components:
                msg = _("Component Valuation Percentage Can Not Be In Negative Value For:\n- %s") % (
                    "\n- ".join(negative_components)
                )
                raise ValidationError(msg)
            # Rule #3: check total > 100
            if float_compare(total, 100.0, precision_digits=6) > 0:
                raise ValidationError(
                    _("Component Valuation Percentage Is Over Than 100 In Total.\nPlease Check The Data Again")
                )
            # Rule #4: check total < 100
            if float_compare(total, 100.0, precision_digits=6) < 0:
                raise ValidationError(
                    _("Component Valuation Percentage Is Less Than 100 In Total.\nPlease Check The Data Again")
                )

        return True
    
    def write(self, vals):
        if 'product_tmpl_id' in vals:
            product_cost = self.env['product.template'].browse(vals['product_tmpl_id']).standard_price
            vals['cost'] = product_cost
        res = super(MrpBom, self).write(vals)
        if self.type == 'phantom':
            self.kit_component_valuation_validation()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(MrpBom, self).create(vals_list)
        if res.type == 'phantom':
            res.kit_component_valuation_validation()

        product_cost = res.product_tmpl_id.standard_price
        res.cost = product_cost
        return res
