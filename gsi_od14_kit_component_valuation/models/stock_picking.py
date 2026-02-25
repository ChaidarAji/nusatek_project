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
