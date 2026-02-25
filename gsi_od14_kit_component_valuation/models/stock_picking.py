from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:

            # Update main product
            bom_ids = picking.move_ids_without_package.mapped('bom_id')
            for bom in bom_ids:
                main_product = bom.product_tmpl_id
                current_qty = main_product.qty_available
                current_cost = main_product.standard_price
                main_cost = picking.move_ids_without_package.filtered(lambda x: x.bom_id == bom)[0].main_cost
                purchase_line_id = picking.move_ids_without_package.filtered(lambda x: x.bom_id == bom)[0].purchase_line_id
                if purchase_line_id:
                    purchase_qty = purchase_line_id[0].product_qty if purchase_line_id else 0.0
                    new_cost = (current_cost * current_qty + main_cost) / (current_qty + purchase_qty)
                    main_product.write({
                        'standard_price': new_cost,
                    })
        res = super(StockPicking, self).button_validate()
        return res

    def _action_done(self):
        """
        Override to prevent additional items added to delivery orders
        from being automatically added back to the sales order.

        The standard sale_stock module (addons/sale_stock/models/stock.py lines 90-122)
        automatically creates new SO lines for any moves in a delivery order that:
        - Are linked to a sale order (picking.sale_id exists)
        - Have destination location usage = 'customer'
        - Are NOT already linked to a SO line (move.sale_line_id is False)
        - Have quantity done > 0

        This override calls the parent but prevents SO line creation by temporarily
        clearing the sale_id from pickings with additional items.
        """
        # Identify pickings with additional items (moves without sale_line_id)
        pickings_with_additional_items = {}
        for picking in self:
            additional_moves = picking.move_lines.filtered(
                lambda m: not m.sale_line_id and picking.sale_id and
                m.location_dest_id.usage == 'customer' and m.quantity_done > 0
            )
            if additional_moves:
                # Store the original sale_id
                pickings_with_additional_items[picking.id] = picking.sale_id.id
                # Temporarily clear sale_id to prevent SO line creation
                picking.write({'sale_id': False})

        # Call parent method - it won't create SO lines because sale_id is False
        res = super(StockPicking, self)._action_done()

        # Restore the sale_id after validation
        for picking_id, sale_id in pickings_with_additional_items.items():
            self.browse(picking_id).write({'sale_id': sale_id})

        return res
