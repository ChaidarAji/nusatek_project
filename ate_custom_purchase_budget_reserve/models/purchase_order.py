import pdb

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    budget_checked = fields.Boolean(string="Budget Checked", default=False, tracking=True)
    committed_reserve_amount = fields.Boolean(string="Committed Reserve Amount", tracking=True)
    revised_reserved_amount = fields.Boolean(string="Revised Reserved Amount",tracking=True)
    revise_reserved_state = fields.Boolean(default=False, compute="_compute_bool", store=True)
    budget_map_ids = fields.One2many('purchase.budget.map', 'order_id', string="Purchase Budget Map")
    all_service = fields.Boolean(default=True, compute="_compute_all_service", store=True)

    @api.depends('order_line.product_id')
    def _compute_all_service(self):
        for rec in self:
            for line in rec.order_line:
                if line.product_id.detailed_type != 'service':
                    rec.all_service = False
                else:
                    rec.all_service = True


    # def _check_analytic_distribution(self, order_id):
    #     for rec in self:
    #         for line in rec.order_line:
    #             if rec.analytic_distribution and line.analytic_distribution:
    #
    #                 if line.analytic_distribution != rec.analytic_distribution:
    #                     raise exceptions.ValidationError(
    #                         _("The analytic distribution on the purchase order line is different from the purchase "
    #                           "order's analytic distribution.")
    #                     )

    def update_analytic_distribution(self):
        for rec in self:

            for line in rec.order_line:
                line.analytic_distribution = rec.analytic_distribution

            rec.generate_budget_map(rec.analytic_distribution)

    @api.depends('state', 'committed_reserve_amount', 'is_shipped')
    def _compute_bool(self):
        for rec in self:
            if rec.state == 'cancel' and rec.committed_reserve_amount:
                rec.revise_reserved_state = True
            if rec.state in ('purchase', 'done') and rec.is_shipped and rec.committed_reserve_amount:
                rec.revise_reserved_state = True
            # else:
            #     rec.revise_reserved_state = False

    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if self.analytic_account_id:
            self.budget_checked = False
            self.analytic_distribution = {
                self.analytic_account_id.id: 100.0
            }
        else:
            self.analytic_distribution = {}

    @api.model_create_multi
    def create(self, vals):
        purchases = super(PurchaseOrder, self).create(vals)
        for purchase in purchases:

            purchase.detect_expense_account()
            purchase.form_checker()
            purchase.generate_budget_map()
        return purchases

    def write(self, vals):

        for rec in self:

            if 'analytic_distribution' in vals or 'order_line' in vals:
                vals['budget_checked'] = False


        res = super(PurchaseOrder, self).write(vals)
        for rec in self:

            rec.detect_expense_account()

            if 'analytic_distribution' in vals or 'order_line' in vals:

                rec.generate_budget_map()

            rec.update_map_record_status()

            for line in rec.order_line:

                line.analytic_distribution = rec.analytic_distribution

                if not line.expense_account_id:
                    raise ValidationError(
                        _("One or More Purchase Order Line Found With No Expense Account Set. "
                          "Please Set Expense Account For Each Purchase Order Line"))

        return res

    def form_checker(self):
        for rec in self:
            for line in rec.order_line:
                if not line.expense_account_id:
                    raise ValidationError(
                        _("One or More Purchase Order Line Found With No Expense Account Set. "
                          "Please Set Expense Account For Each Purchase Order Line"))

    def generate_budget_map(self):

        budget_rec = self.env['crossovered.budget']
        budgetary_position_rec = self.env['account.budget.post']
        budget_line_rec = self.env['crossovered.budget.lines']
        purchase_budget_map_rec = self.env['purchase.budget.map']

        for rec in self:

            new_budget_maps = []

            # if rec.budget_map_ids:

                # print("UNLINK")
                # rec.budget_map_ids.unlink()

            analytic_account_id = rec.analytic_account_id
            if not analytic_account_id:
                continue

            budget_data = budget_rec.search([('analytic_account_ids', '=', analytic_account_id.id), ('state', '=', 'validate')])

            if not budget_data:
                # continue
                #UcaSam's code : detect only validated budget data
                raise ValidationError("NO VALIDATED BUDGET DATA FOUND. "
                                                      "Please Check Your Budget Record, Make Sure It Is In VALIDATED State")

            #UcaSam's code : budget lines are always stored in company currency
            company_id = rec.company_id
            company_currency = company_id.currency_id
            conversion_date = (rec.date_order or fields.Datetime.now()).date()

            for line in rec.order_line:

                expense_account_id = line.expense_account_id

                budget_post = budgetary_position_rec.search([('account_ids', 'in', expense_account_id.id)])

                #UcaSam's code : convert the line subtotal when the order uses a foreign currency
                line_amount = line.price_subtotal
                if company_currency and rec.currency_id and rec.currency_id != company_currency:
                    line_amount = company_currency._convert(
                        line_amount, rec.currency_id, company_id, conversion_date)

                base_vals = {
                    'po_line_id': line.id,
                    'product_id': line.product_id.product_tmpl_id.id,
                    'expense_account_id': expense_account_id.id,
                    'analytic_account_id': analytic_account_id.id,
                    'uom': line.product_uom.id,
                    'amount': line_amount,
                }

                if budget_post:

                    for b_post in budget_post:

                        budget_line_id = budget_line_rec.search([('analytic_account_id', '=', analytic_account_id.id),
                                                                 ('general_budget_id', '=', b_post.id),
                                                                 ('crossovered_budget_id', '=', budget_data.id)], limit=1)
                        vals = base_vals.copy()
                        vals.update({
                            'detected_budgetary_position': b_post.id,
                            'status': 'unchecked' if budget_line_id else 'non_listed_budgetary',
                            'remaining_amt': budget_line_id.available_amt_for_reserve if budget_line_id else 0.0,
                        })
                        new_budget_maps.append((0, 0, vals))

                else:

                    vals = base_vals.copy()
                    vals.update({
                        'detected_budgetary_position': False,
                        'status': 'no_expense',
                        'remaining_amt': 0.0,
                    })
                    new_budget_maps.append((0, 0, vals))

            rec.write({'budget_map_ids': [(5, 0, 0)] + new_budget_maps})

                #         if budget_line_id:
                #
                #             vals = {'order_id': rec.id,
                #                     'po_line_id': line.id,
                #                     'product_id': product_id.product_tmpl_id.id,
                #                     'expense_account_id': expense_account_id.id,
                #                     'analytic_account_id': analytic_account_id.id,
                #                     'uom': uom_id.id,
                #                     'detected_budgetary_position': b_post.id,
                #                     'status': 'unchecked',
                #                     'remaining_amt': budget_line_id.available_amt_for_reserve,
                #                     'amount': subtotal }
                #
                #             purchase_budget_map_rec.create(vals)
                #
                #         else:
                #
                #             vals = {'order_id': rec.id,
                #                     'po_line_id': line.id,
                #                     'product_id': product_id.product_tmpl_id.id,
                #                     'expense_account_id': expense_account_id.id,
                #                     'analytic_account_id': analytic_account_id.id,
                #                     'uom': uom_id.id,
                #                     'detected_budgetary_position': b_post.id,
                #                     'status': 'non_listed_budgetary',
                #                     'remaining_amt': 0.0,
                #                     'amount': subtotal}
                #
                #             purchase_budget_map_rec.create(vals)
                #
                # else:
                #
                #     vals = {'order_id': rec.id,
                #             'po_line_id': line.id,
                #             'product_id': product_id.product_tmpl_id.id,
                #             'expense_account_id': expense_account_id.id,
                #             'analytic_account_id': analytic_account_id.id,
                #             'uom': uom_id.id,
                #             'detected_budgetary_position': False,
                #             'status': 'no_expense',
                #             'remaining_amt': 0.0,
                #             'amount': subtotal}
                #
                #     purchase_budget_map_rec.create(vals)

    # def generate_budget_map(self, analytic_distribution):
    #     budget_line_rec = self.env['crossovered.budget.lines']
    #     budgetary_position_rec = self.env['account.budget.post']
    #     purchase_budget_map_rec = self.env['purchase.budget.map']
    #     budgetary_position_list = []
    #     final_budgetary_list = []
    #     analytic_account_id = False
    #     for rec in self:
    #         if rec.budget_map_ids:
    #             rec.budget_map_ids.unlink()
    #         for line in rec.order_line:
    #             percentage = 0.0
    #
    #             if line.expense_account_id and analytic_distribution:
    #
    #                 analytic_distributions = analytic_distribution
    #
    #                 for distribution in analytic_distributions:
    #                     percentage = analytic_distributions.get(distribution, 0.0)
    #                     budget_line_ids = budget_line_rec.search([('analytic_account_id', '=', int(distribution))])
    #                     if budget_line_ids:
    #                         for b_line in budget_line_ids:
    #                             budgetary_position_list.append(b_line.general_budget_id.id)
    #                             final_budgetary_list = list(set(budgetary_position_list))
    #                             analytic_account_id = int(distribution)
    #
    #             if final_budgetary_list:
    #                 for b_post in final_budgetary_list:
    #                     budgetary_position_id = budgetary_position_rec.browse(b_post)
    #                     if budgetary_position_id.account_ids:
    #                         amount = line.price_subtotal * (percentage / 100.0)
    #                         for account in budgetary_position_id.account_ids:
    #                             if account.id == line.expense_account_id.id:
    #                                 vals = {'order_id': rec.id,
    #                                         'po_line_id': line.id,
    #                                         'product_id': line.product_id.product_tmpl_id.id,
    #                                         'expense_account_id': line.expense_account_id.id,
    #                                         'analytic_account_id': analytic_account_id,
    #                                         'uom': line.product_uom.id,
    #                                         'detected_budgetary_position': b_post,
    #                                         'amount': amount or 0.0}
    #
    #                                 purchase_budget_map_rec.create(vals)

    # def generate_budget_map_general(self):
    #     budget_line_rec = self.env['crossovered.budget.lines']
    #     budgetary_position_rec = self.env['account.budget.post']
    #     purchase_budget_map_rec = self.env['purchase.budget.map']
    #     budgetary_position_list = []
    #     final_budgetary_list = []
    #     analytic_account_id = False
    #     for rec in self:
    #         if rec.budget_map_ids:
    #             rec.budget_map_ids.unlink()
    #         for line in rec.order_line:
    #             percentage = 0.0
    #
    #             if line.expense_account_id and line.analytic_distribution:
    #
    #                 analytic_distributions = line.analytic_distribution
    #
    #                 for distribution in analytic_distributions:
    #                     percentage = analytic_distributions.get(distribution, 0.0)
    #                     budget_line_ids = budget_line_rec.search([('analytic_account_id', '=', int(distribution))])
    #                     if budget_line_ids:
    #                         for b_line in budget_line_ids:
    #                             budgetary_position_list.append(b_line.general_budget_id.id)
    #                             final_budgetary_list = list(set(budgetary_position_list))
    #                             analytic_account_id = int(distribution)
    #
    #             if final_budgetary_list:
    #                 for b_post in final_budgetary_list:
    #                     budgetary_position_id = budgetary_position_rec.browse(b_post)
    #                     if budgetary_position_id.account_ids:
    #                         amount = line.price_subtotal * (percentage / 100.0)
    #                         for account in budgetary_position_id.account_ids:
    #                             if account.id == line.expense_account_id.id:
    #                                 vals = {'order_id': rec.id,
    #                                         'po_line_id': line.id,
    #                                         'product_id': line.product_id.product_tmpl_id.id,
    #                                         'expense_account_id': line.expense_account_id.id,
    #                                         'analytic_account_id': analytic_account_id,
    #                                         'uom': line.product_uom.id,
    #                                         'detected_budgetary_position': b_post,
    #                                         'amount': amount or 0.0}
    #
    #                                 purchase_budget_map_rec.create(vals)

    def update_map_record_status(self):
        insufficient_budget_list = []
        budgetary_position_rec = self.env['account.budget.post']
        purchase_budget_map_obj = self.env['purchase.budget.map']

        self.env.cr.execute("""
            SELECT
                detected_budgetary_position AS dbp,
                MAX(remaining_amt) AS remaining_amt,
                SUM(amount) AS amount
            FROM
                purchase_budget_map
            WHERE
                status IN %s
                AND order_id = %s
                AND detected_budgetary_position IS NOT NULL
            GROUP BY
                detected_budgetary_position
        """, (('unchecked', 'insufficient'), self.id))

        result = self.env.cr.dictfetchall()

        if result:
            for rec in result:
                dbp_id = rec['dbp']
                remaining_amt = rec.get('remaining_amt', 0.0) or 0.0
                total_amount = rec.get('amount', 0.0) or 0.0

                check_available = remaining_amt - total_amount
                budgetary_position_id = budgetary_position_rec.browse(dbp_id)

                map_records = purchase_budget_map_obj.search([
                    ('order_id', '=', self.id),
                    ('detected_budgetary_position', '=', dbp_id),
                    ('status', 'in', ('unchecked', 'insufficient')),
                ])

                if check_available < 0.0:
                    insufficient_budget_list.append(budgetary_position_id.name)
                    map_records.write({'status': 'insufficient'})
                else:
                    map_records.write({'status': 'ok'})

    def check_reserve_budget_limit(self):

        self.generate_budget_map()

        non_listed_account = []
        non_listed_budgetary_position = []
        insufficient_budget_list = []

        budgetary_position_rec = self.env['account.budget.post']

        for line in self.budget_map_ids:

            expense_account_id = line.expense_account_id

            if line.status == 'no_expense':

                non_listed_account.append(expense_account_id.name)

            detected_budgetary_position_id = line.detected_budgetary_position
            budget_status = line.status

            if detected_budgetary_position_id and budget_status == 'non_listed_budgetary':

                non_listed_budgetary_position.append(detected_budgetary_position_id.name)

        self.env.cr.execute("""
            SELECT
                id as id,
                detected_budgetary_position as dbp,
                SUM(remaining_amt) AS remaining_amt,
                SUM(amount) AS amount
            FROM
                purchase_budget_map
            WHERE
                status in %s AND order_id = %s
            GROUP BY id,
                detected_budgetary_position
        """, (('unchecked', 'insufficient', 'ok'), self.id))

        result = self.env.cr.dictfetchall()

        if result:
            grouped_budget = defaultdict(lambda: {
                'remaining_amt': 0.0,
                'amount': 0.0,
            })

            for rec in result:
                dbp_id = rec['dbp']
                grouped_budget[dbp_id]['amount'] += rec.get('amount', 0.0)
                grouped_budget[dbp_id]['remaining_amt'] = rec.get('remaining_amt', 0.0)

            for dbp_id, vals in grouped_budget.items():
                check_available = vals['remaining_amt'] - vals['amount']
                budgetary_position_id = budgetary_position_rec.browse(dbp_id)

                if check_available < 0.0:
                    insufficient_budget_list.append(budgetary_position_id.name)

        non_listed_account = list(dict.fromkeys(non_listed_account))
        non_listed_budgetary_position = list(dict.fromkeys(non_listed_budgetary_position))
        insufficient_budget_list = list(dict.fromkeys(insufficient_budget_list))

        if non_listed_account or non_listed_budgetary_position or insufficient_budget_list:

            self.write({'budget_checked': False})

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'budget.warning.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_non_listed_account': ", ".join(non_listed_account),
                    'default_non_listed_budgetary_position': ", ".join(non_listed_budgetary_position),
                    'default_insufficient_budget_list': ", ".join(insufficient_budget_list),
                }
            }

        else:

            self.budget_checked = True

            return None


    # def check_reserve_budget_limit(self):
    #     budget_line_rec = self.env['crossovered.budget.lines']
    #     grouped_lines = {}
    #     for rec in self:
    #
    #         grouped_lines = defaultdict(lambda: {'lines': [], 'amount': 0.0})
    #
    #         if rec.budget_map_ids:
    #
    #             for line in rec.budget_map_ids:
    #                 key = (line.analytic_account_id.id, line.detected_budgetary_position.id)
    #
    #                 grouped_lines[key]['lines'].append(line)
    #
    #                 grouped_lines[key]['amount'] += line.amount
    #
    #             for (analytic_account_id, detected_budgetary_position), lines in grouped_lines.items():
    #                 budget_line_ids = budget_line_rec.search([('analytic_account_id', '=', analytic_account_id),
    #                                                          ('general_budget_id', '=', detected_budgetary_position),
    #                                                          ('crossovered_budget_state', '=', 'validate')])
    #                 if budget_line_ids:
    #                     for b_line in budget_line_ids:
    #                         if lines['amount'] <= b_line.available_amt_for_reserve:
    #                             rec.write({'budget_checked': True})
    #
    #                         else:
    #                             raise ValidationError("One or More Purchase Item Have Insufficient Budget. "
    #                                                   "Please Check Your Budget Record")
    #
    #             if not len(rec.budget_map_ids) == len(rec.order_line):
    #                 rec.write({'budget_checked': False})

    def button_confirm(self):

        res = super(PurchaseOrder, self).button_confirm()

        for rec in self:

            #UcaSam's code: re-check budget limit
            rec.check_reserve_budget_limit()
            rec.confirm_reserve_budget_amount()

        return res

    def confirm_reserve_budget_amount(self):
        budget_line_rec = self.env['crossovered.budget.lines']
        grouped_lines = {}
        for rec in self:

            if rec.order_line:

                for p_line in rec.order_line:

                    if not p_line.analytic_distribution:
                        raise ValidationError("Please update analytic account for all purchase order lines!")

            grouped_lines = defaultdict(lambda: {'lines': [], 'amount': 0.0})

            if rec.budget_checked:

                if rec.budget_map_ids:

                    for line in rec.budget_map_ids:
                        key = (line.analytic_account_id.id, line.detected_budgetary_position.id)

                        grouped_lines[key]['lines'].append(line)

                        grouped_lines[key]['amount'] += line.amount

                    for (analytic_account_id, detected_budgetary_position), lines in grouped_lines.items():
                        budget_line_ids = budget_line_rec.search([('analytic_account_id', '=', analytic_account_id),
                                                                  ('general_budget_id', '=',
                                                                   detected_budgetary_position),
                                                                  ('crossovered_budget_state', '=', 'validate')])
                        if budget_line_ids:
                            for b_line in budget_line_ids:
                                reserved_amount = b_line.reserved_amount + lines['amount']
                                available_reserved_amount = b_line.available_amt_for_reserve - lines['amount']
                                b_line.write({'reserved_amount': reserved_amount,
                                              'available_amt_for_reserve': available_reserved_amount})

                    rec.committed_reserve_amount = True

            else:
                raise ValidationError("The Budget Data Was Updated, Please Do Check The Budget For This Transaction "
                                      "Again By Clicking The Check Budget Button")

    def revise_reserved_amount(self):
        budget_line_rec = self.env['crossovered.budget.lines']
        all_service = False
        for rec in self:
            if rec.is_shipped:
                if not rec.revised_reserved_amount:
                    if rec.budget_map_ids:
                        for b_line in rec.budget_map_ids:

                            # revised_amount = ((b_line.amount / b_line.po_line_id.product_qty) *
                            #                   (b_line.po_line_id.product_qty - b_line.po_line_id.qty_received))

                            #UcaSam's code: Calculate the revised reserve amount based on invoiced qty
                            revised_amount = ((b_line.amount / b_line.po_line_id.product_qty) *
                                              (b_line.po_line_id.product_qty - b_line.po_line_id.qty_invoiced))

                            budget_line_ids = budget_line_rec.search([('analytic_account_id', '=', b_line.analytic_account_id.id),
                                                                      ('general_budget_id', '=', b_line.detected_budgetary_position.id),
                                                                      ('crossovered_budget_state', '=', 'validate')])
                            for budget_line in budget_line_ids:
                                reserved_amount = budget_line.reserved_amount - revised_amount
                                available_amt_for_reserve = budget_line.available_amt_for_reserve + revised_amount
                                budget_line.write({'reserved_amount': reserved_amount,
                                                   'available_amt_for_reserve': available_amt_for_reserve})

                        rec.revised_reserved_amount = True

                else:
                    raise ValidationError(_("Already Revised Budget Reserved Amount For This Purchase"))

            else:

                #UcaSam's code: Temporary allow revise reserved amount, ignoring is_shipped boolean

                if rec.all_service is True:
                    if not rec.revised_reserved_amount:
                        if rec.budget_map_ids:
                            for b_line in rec.budget_map_ids:

                                # revised_amount = ((b_line.amount / b_line.po_line_id.product_qty) *
                                #                   (b_line.po_line_id.product_qty - b_line.po_line_id.qty_received))

                                #UcaSam's code: Calculate the revised reserve amount based on invoiced qty
                                revised_amount = ((b_line.amount / b_line.po_line_id.product_qty) *
                                                  (b_line.po_line_id.product_qty - b_line.po_line_id.qty_invoiced))

                                budget_line_ids = budget_line_rec.search([('analytic_account_id', '=', b_line.analytic_account_id.id),
                                                                          ('general_budget_id', '=', b_line.detected_budgetary_position.id),
                                                                          ('crossovered_budget_state', '=', 'validate')])
                                for budget_line in budget_line_ids:
                                    reserved_amount = budget_line.reserved_amount - revised_amount
                                    available_amt_for_reserve = budget_line.available_amt_for_reserve + revised_amount
                                    budget_line.write({'reserved_amount': reserved_amount,
                                                       'available_amt_for_reserve': available_amt_for_reserve})

                            rec.revised_reserved_amount = True

                    else:
                        raise ValidationError(_("Already Revised Budget Reserved Amount For This Purchase"))

                else:

                    raise ValidationError(_("Can't Create Purchase Budget Reserve Revision for On Going Purchase Shipment. "
                                            "Please Make Sure All Shipments Are Completed If you Need To Revise The "
                                            "Purchase Budget Reserve Amount"))
                #Code ends here

    def detect_expense_account(self):
        for rec in self:
            for line in rec.order_line:
                if line.product_id.property_account_expense_id:
                    line.expense_account_id = line.product_id.property_account_expense_id.id
                elif line.product_id.categ_id.property_account_expense_categ_id:
                    line.expense_account_id = line.product_id.categ_id.property_account_expense_categ_id.id
                else:
                    line.have_expense_account = False


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    expense_account_id = fields.Many2one('account.account', string="Expense Account")
    have_expense_account = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        if 'order_id' in vals:
            order = self.env['purchase.order'].browse(vals['order_id'])
            if order.analytic_distribution:
                # Set the analytic distribution from the purchase order
                vals['analytic_distribution'] = order.analytic_distribution
        return super(PurchaseOrderLine, self).create(vals)

    @api.onchange('expense_account_id')
    def onchange_expense_account_id(self):
        if self.expense_account_id:
            self.have_expense_account = True
        else:
            self.have_expense_account = False


class PurchaseBudgetMap(models.Model):
    _name = "purchase.budget.map"
    _description = "Purchase Budget Map"

    order_id = fields.Many2one('purchase.order', string="Purchase Order")
    po_line_id = fields.Many2one('purchase.order.line', string="PO Line ID")
    product_id = fields.Many2one('product.template', string="Product")
    uom = fields.Many2one('uom.uom', string="UoM")
    currency_id = fields.Many2one(related="order_id.currency_id", string="Currency", store=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    expense_account_id = fields.Many2one('account.account', string="Expense Account")
    detected_budgetary_position = fields.Many2one('account.budget.post', string="Detected Budgetary Position")
    amount = fields.Monetary(string="Will Be Reserved From This Transaction")
    status = fields.Selection([('unchecked', 'Unchecked'), ('ok', 'OK'),
                               ('insufficient', 'Insufficient'), ('no_expense', 'Expense Account Not Found'),
                               ('non_listed_budgetary', 'Non-Listed Budgetary')], string="Budget Status", default="unchecked")
    remaining_amt = fields.Monetary(string="Remaining(Current)")





