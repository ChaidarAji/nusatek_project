from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'


    def create_returns(self):

        for wizard in self:

            if wizard.picking_id.purchase_id:

                if wizard.picking_id.purchase_id.is_shipped:

                    raise ValidationError(_("Cannot Create Return Transaction Related To Completed Purchase Order "
                                            "Transaction. IF Really Need To Make This Return Transaction, "
                                            "Please Create Return Transaction Manually From Inventory Menu And Mention "
                                            "This Shipment Number As Reference"))

        return super().create_returns()