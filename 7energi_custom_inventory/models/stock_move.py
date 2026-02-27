from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.onchange('product_id')
    def _onchange_product_id_desc_picking(self):
        for move in self:
            if move.product_id:
                move.description_picking = move.product_id.name
            else:
                move.description_picking = ""

    def create(self, vals):
        res = super(StockMove, self).create(vals)
        for move in res:
            if not move.description_picking:
                move._onchange_product_id_desc_picking()
        return res

    def unlink(self):
        for data in self:
            picking = data.move_line_ids.mapped('picking_id') | data.picking_id
            if not picking:
                picking = data._search_picking_for_assignation()
            if picking and picking.sale_id:
                if any(move.state not in ('draft', 'cancel') and move.sale_line_id for move in data):
                    raise UserError(_('You can only delete draft moves.'))
            else:
                if any(move.state not in ('draft', 'cancel') for move in data):
                    raise UserError(_('You can only delete draft moves.'))
            # With the non plannified picking, draft moves could have some move lines.
            data.with_context(prefetch_fields=False).mapped('move_line_ids').unlink()
        return True