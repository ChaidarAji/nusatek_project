from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # def action_stock_return_picking(self):
    #     # self.return_reserved_budget_checker()
    #     print("-------------", self.purchase_id)
    #     # for rec in self:
    #     #     if rec.purchase_id:
    #     #         if rec.purchase_id.is_shipped:
    #     #             raise ValidationError(_("Cannot Create Return Transaction Related To Completed Purchase Order "
    #     #                                     "Transaction. IF Really Need To Make This Return Transaction, "
    #     #                                     "Please Create Return Transaction Manually From Inventory Menu And Mention "
    #     #                                     "This Shipment Number As Reference"))
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Reverse Transfer',
    #         'view_mode': 'form',
    #         'res_model': 'stock.return.picking',
    #         'target': 'new',
    #         'context': {
    #         'default_picking_id': self.id,
    #     }
    #     }
    #
    # def return_reserved_budget_checker(self):
    #     for rec in self:
    #         if rec.purchase_id:
    #             if rec.purchase_id.is_shipped:
    #                 raise ValidationError(_("Cannot Create Return Transaction Related To Completed Purchase Order "
    #                                         "Transaction. IF Really Need To Make This Return Transaction, "
    #                                         "Please Create Return Transaction Manually From Inventory Menu And Mention "
    #                                         "This Shipment Number As Reference"))

