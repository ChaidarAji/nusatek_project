# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare

# DICS ADD CODE
class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        context_dict = dict(self.env.context)  # start with existing context
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                context_dict['run_negative_stock_check'] = True
                skip_check = True
                q_quantity_map = {}
                for move in picking.move_ids_without_package.filtered(lambda m: m.product_id.type == 'product'):
                    product = move.product_id
                    move_lines = move.move_line_ids
                    qty_done = sum(move_lines.mapped('qty_done')) if move_lines else move.product_uom_qty
                    on_hand_qty = product.with_context(location=picking.location_id.id).qty_available
                    q_quantity = on_hand_qty - qty_done
                    q_quantity_map[product.id] = q_quantity
                    if on_hand_qty < qty_done:
                        skip_check = False
                context_dict['q_quantity_map'] = q_quantity_map
                if skip_check:
                    context_dict['skip_negative_qty_check'] = True
            else:
                context_dict['skip_negative_qty_check'] = True
        return super(StockPicking, self.with_context(context_dict)).button_validate()


