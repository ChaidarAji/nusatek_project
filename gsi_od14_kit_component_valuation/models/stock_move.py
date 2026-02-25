from odoo import models, fields, api
from odoo.tools import float_compare, float_is_zero

class StockMove(models.Model):
    _inherit = 'stock.move'

    kit_component = fields.Boolean(string="Kit Component", default=False)
    bom_id = fields.Many2one("mrp.bom", string="BoM ID")
    kit_valuation_percentage = fields.Float(string="Kit Valuation Percentage", default=0.0)
    cost_currency_id = fields.Many2one("res.currency", related="product_tmpl_id.cost_currency_id")
    main_cost = fields.Monetary(string="Main Cost", default=0.0, currency_field='cost_currency_id')
    component_cost = fields.Monetary(string="Component Cost", default=0.0, currency_field='cost_currency_id')


    def _prepare_phantom_move_values(self, bom_line, product_qty, quantity_done):
        vals = super(StockMove, self)._prepare_phantom_move_values(bom_line, product_qty, quantity_done)
        purchase_line_id = self.purchase_line_id
        main_product_tax_amount = purchase_line_id.price_tax
        main_cost = purchase_line_id.price_subtotal + main_product_tax_amount
        kit_valuation_percentage = bom_line.component_valuation_percentage/100 if bom_line.component_valuation_percentage else 0.0
        component_cost = main_cost * kit_valuation_percentage
        vals.update({
            'kit_component': True,
            'bom_id': bom_line.bom_id.id,
            'kit_valuation_percentage': kit_valuation_percentage,
            'main_cost': main_cost,
            'component_cost': component_cost,
        })
        return vals

    def _get_price_unit(self):
        """ Returns the unit price to value this stock move """
        self.ensure_one()
        price_unit = self.price_unit
        precision = self.env['decimal.precision'].precision_get('Product Price')
        # If the move is a return, use the original move's price unit.
        if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
            # dropshipping create additional positive svl to make sure there is no impact on the stock valuation
            # We need to remove them from the computation of the price unit.
            if self.origin_returned_move_id._is_dropshipped() or self.origin_returned_move_id._is_dropshipped_returned():
                layers = layers.filtered(lambda l: float_compare(l.value, 0, precision_rounding=l.product_id.uom_id.rounding) <= 0)
            layers |= layers.stock_valuation_layer_ids
            quantity = sum(layers.mapped("quantity"))
            return sum(layers.mapped("value")) / quantity if not float_is_zero(quantity, precision_rounding=layers.uom_id.rounding) else 0
        if self.kit_component:
            return self.component_cost/self.product_uom_qty
        return price_unit if not float_is_zero(price_unit, precision) or self._should_force_price_unit() else self.product_id.standard_price


    def action_explode(self):
        res = super(StockMove, self).action_explode()
        for move in self:
            sale_line_id = move.sale_line_id
            if sale_line_id:
                product_id = sale_line_id.product_id
                bom_id = self.env['mrp.bom']._bom_find(product=product_id, company_id=move.company_id.id, bom_type='phantom')
                if bom_id:
                    move.bom_id = bom_id.id
                if move.product_id in bom_id.bom_line_ids.mapped('product_id'):
                    move.kit_component = True
        return res