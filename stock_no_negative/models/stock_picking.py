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
                for move in picking.move_ids_without_package.filtered(lambda m: m.product_id.type == 'product'):
                    product = move.product_id
                    qty_done = sum(move.move_line_ids.mapped('qty_done')) or move.product_uom_qty
                    on_hand_qty = product.with_context(location=picking.location_id.id).qty_available
                    q_quantity = on_hand_qty - qty_done
                    context_dict['q_quantity'] = q_quantity
                    if on_hand_qty < qty_done:
                        skip_check = False
                        break
                if skip_check:
                    context_dict['skip_negative_qty_check'] = True
            else:
                context_dict['skip_negative_qty_check'] = True
        return super(StockPicking, self.with_context(context_dict)).button_validate()


