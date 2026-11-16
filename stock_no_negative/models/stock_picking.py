# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare

# DICS ADD CODE
class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        # GSI-ATE-004: Negative Stock Checker for Internals
        self._check_negative_stock_internal()

        context_dict = dict(self.env.context)  # start with existing context
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                context_dict['run_negative_stock_check'] = True
                skip_check = True
                q_quantity_map = {}
                for move in picking.move_ids_without_package.filtered(lambda m: m.product_id.type == 'product'):
                    product = move.product_id
                    move_lines = move.move_line_ids
                    qty_done = sum(move_lines.mapped('quantity')) if move_lines else move.product_uom_qty
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

    def _check_negative_stock_internal(self):
        """Negative Stock Checker for Internals (GSI-ATE-004).

        For every stockable product of an internal transfer, compare the
        "Demand" quantity with the quantity available in the source location
        and block the validation when the demand is greater.
        """
        # Allow callers to bypass the check, same as the stock.quant constraint
        if self.env.context.get("skip_negative_qty_check"):
            return
        # Do not interfere with other modules' tests unless explicitly asked
        if config["test_enable"] and not self.env.context.get("test_stock_no_negative"):
            return

        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        for picking in self.filtered(lambda p: p.picking_type_id.code == "internal"):
            # 1. Loop each product; sum the demand (in product UoM) per
            #    product and source location
            demand_map = defaultdict(float)
            moves = picking.move_ids.filtered(
                lambda m: m.product_id.type == "product"
                and m.state not in ("done", "cancel")
            )
            for move in moves:
                demand_map[(move.product_id, move.location_id)] += move.product_qty

            for (product, location), demand in demand_map.items():
                if (
                    location.usage not in ("internal", "transit")
                    or product.allow_negative_stock
                    or product.categ_id.allow_negative_stock
                    or location.allow_negative_stock
                ):
                    continue
                # 3a. Available qty of the product in the source location
                available_qty = product.with_context(
                    location=location.id
                ).qty_available
                # 3b. Demand > Available qty -> raise warning
                if float_compare(demand, available_qty, precision_digits=precision) > 0:
                    lots = picking.move_line_ids.filtered(
                        lambda ml, p=product: ml.product_id == p and ml.lot_id
                    ).lot_id
                    name_lot = (
                        _(" lot {}").format(", ".join(lots.mapped("display_name")))
                        if lots
                        else ""
                    )
                    raise ValidationError(
                        _(
                            "You cannot validate this stock operation because the "
                            "stock level of the product '{name}'{name_lot} would "
                            "become negative. ({available_qty}) on the stock "
                            "location '{complete_name}' and negative stock is "
                            "not allowed for this product and/or location."
                        ).format(
                            name=product.display_name,
                            name_lot=name_lot,
                            available_qty=available_qty,
                            complete_name=location.complete_name,
                        )
                    )
