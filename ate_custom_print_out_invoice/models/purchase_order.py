from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    site_id = fields.Char(
        string="Site ID",
        # readonly=True,
    )
    site_name = fields.Char(
        string="Site Name",
        # readonly=True,
    )

    def _prepare_account_move_line(self, move=False):
        invoice_line_vals = super(PurchaseOrderLine, self)._prepare_account_move_line(move=False)
        invoice_line_vals['site_id'] = self.site_id
        invoice_line_vals['site_name'] = self.site_name
        # Only override if PO currency ≠ company currency
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            # Conversion with proper date & company
            date = move and move.date or fields.Date.today()
            invoice_line_vals['balance'] = self.company_id.currency_id._convert(
                self.price_unit_discounted * self.qty_to_invoice,
                self.currency_id,
                self.company_id,
                date,
                round=False,
            )
        return invoice_line_vals
