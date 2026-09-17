# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        invoice_line_vals = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)

        sale_order = self.order_id

        invoice_line_vals['site_id'] = self.site_id
        invoice_line_vals['site_name'] = self.site_name

        if not self.is_downpayment:
            invoice_line_vals['quantity_ordered'] = self.product_uom_qty
        else:
            total_quantity_ordered = sum(line.product_uom_qty for line in sale_order.order_line)
            invoice_line_vals['quantity_ordered'] = total_quantity_ordered

        return invoice_line_vals
