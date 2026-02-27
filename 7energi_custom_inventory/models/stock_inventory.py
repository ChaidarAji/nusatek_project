# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    # Override inventory_date to make it editable and importable
    inventory_date = fields.Datetime(
        'Inventory Date',
        readonly=False,  # Make it editable
        default=fields.Datetime.now,
        help="Last date at which the On Hand Quantity has been computed."
    )

    def _get_move_values(self, qty, location_id, location_dest_id, out):
        """Override to use the line's inventory_date instead of the header's date"""
        vals = super(StockInventoryLine, self)._get_move_values(qty, location_id, location_dest_id, out)
        # Use the line's inventory_date instead of the header's date
        if self.inventory_date:
            vals['date'] = self.inventory_date
        return vals


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _create_in_svl(self, forced_quantity=None):
        """Override to pass inventory_date to SVL creation via context"""
        # If this move is from an inventory adjustment, pass the inventory date via context
        if self.inventory_id:
            inventory_lines = self.env['stock.inventory.line'].search([
                ('inventory_id', '=', self.inventory_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if inventory_lines and inventory_lines.inventory_date:
                self = self.with_context(force_svl_date=inventory_lines.inventory_date)
        return super(StockMove, self)._create_in_svl(forced_quantity=forced_quantity)

    def _create_out_svl(self, forced_quantity=None):
        """Override to pass inventory_date to SVL creation via context"""
        # If this move is from an inventory adjustment, pass the inventory date via context
        if self.inventory_id:
            inventory_lines = self.env['stock.inventory.line'].search([
                ('inventory_id', '=', self.inventory_id.id),
                ('product_id', '=', self.product_id.id)
            ], limit=1)
            if inventory_lines and inventory_lines.inventory_date:
                self = self.with_context(force_svl_date=inventory_lines.inventory_date)
        return super(StockMove, self)._create_out_svl(forced_quantity=forced_quantity)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    @api.model_create_multi
    def create(self, vals_list):
        """Override to force set create_date from context if provided"""
        # Create the records normally first
        records = super(StockValuationLayer, self).create(vals_list)

        # If force_svl_date is in context, update create_date via SQL
        force_date = self._context.get('force_svl_date')
        if force_date:
            # Convert datetime to string format for SQL
            if isinstance(force_date, str):
                date_str = force_date
            else:
                date_str = fields.Datetime.to_string(force_date)

            # Update create_date via SQL (ORM doesn't allow writing to create_date)
            for record in records:
                self.env.cr.execute("""
                    UPDATE stock_valuation_layer
                    SET create_date = %s
                    WHERE id = %s
                """, (date_str, record.id))

            # Invalidate cache to ensure the updated values are read
            records.invalidate_cache(['create_date'])

        return records

