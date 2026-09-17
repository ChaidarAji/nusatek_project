# -*- coding: utf-8 -*-

from odoo import models, fields, api

try:
    from num2words import num2words
except ImportError:
    num2words = None

# Odoo's currency_unit_label / currency_subunit_label are in English
# ("Rupiah"/"Cents", "Dollars"/"Cents"), so map the Indonesian wording by ISO code.
CURRENCY_LABELS_ID = {
    'IDR': ('Rupiah', 'Sen'),
    'USD': ('Dolar Amerika Serikat', 'Sen'),
    'SGD': ('Dolar Singapura', 'Sen'),
    'EUR': ('Euro', 'Sen'),
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    bukti_potong = fields.Char(
        string='Bukti Potong'
    )

    termin = fields.Boolean(
        string="Termin (%)",
        default=True
    )

    print_count = fields.Integer(
        string="Print Count",
        default=0,
        readonly=True
    )

    def _num2words_id(self, number):
        """Terbilang: ubah angka menjadi kata dalam Bahasa Indonesia."""
        try:
            return num2words(number, lang='id').title()
        except NotImplementedError:
            return num2words(number, lang='en').title()

    def text_indonesian(self):
        self.ensure_one()
        if num2words is None:
            return ''

        currency = self.currency_id
        unit_label, subunit_label = CURRENCY_LABELS_ID.get(
            currency.name,
            (currency.currency_unit_label, currency.currency_subunit_label),
        )

        amount = self.amount_total
        sign = 'Minus ' if amount < 0 else ''

        # Split the same way amount_to_text() does, so the words match the printed figure.
        formatted = "%.{0}f".format(currency.decimal_places) % abs(amount)
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        amount_words = '%s%s %s' % (
            sign, self._num2words_id(integer_value), unit_label,
        )
        if fractional_value:
            amount_words += ' %s %s' % (
                self._num2words_id(fractional_value), subunit_label,
            )
        return amount_words

    @api.model
    def _increment_print_count(self):
        for record in self:
            record.print_count += 1

    # dics custom code add
    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        for move in self:
            for line in move.line_ids:
                # Only act on lines where your custom currency logic applies
                if line.currency_id and line.amount_currency and line.currency_id != line.company_id.currency_id:
                    # Convert amount_currency to company currency
                    company_currency = line.move_id.company_id.currency_id
                    balance = company_currency._convert(
                        line.amount_currency,
                        line.currency_id,
                        line.move_id.company_id,
                        line.date or fields.Date.today(),
                        round=False,
                    )
                    line.with_context(skip_custom_balance=True).balance = balance


class ReportAteInvoice(models.AbstractModel):
    _name = 'report.ate_custom_print_out_invoice.report_ate_invoice_document'
    _description = 'Custom Report for ATE Invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['account.move'].browse(docids)
        records._increment_print_count()
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': records,
            'is_original': records[0].print_count == 1
        }


class ReportInvoiceDocument(models.AbstractModel):
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['account.move'].browse(docids)
        records._increment_print_count()
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': records,
            'is_original': records[0].print_count == 1
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    quantity_ordered = fields.Float(
        string='Quantity Ordered',
        readonly=True
    )

    site_id = fields.Text(
        string='Site ID',
        readonly=True
    )
    site_name = fields.Text(
        string='Site Name',
        readonly=True
    )

    termin_percentage = fields.Char(
        string="Termin Percentage",
        compute='_compute_termin_percentage',
        store=True
    )

    @api.depends('quantity', 'move_id.termin')
    def _compute_termin_percentage(self):
        for line in self:
            if line.move_id.termin:
                line.termin_percentage = f"{line.quantity}%"
            else:
                line.termin_percentage = str(line.quantity)

    # @api.depends('move_id', 'currency_id', 'amount_currency')
    @api.depends('move_id')
    def _compute_balance(self):
        # First, call the base computation
        res = super(AccountMoveLine, self)._compute_balance()
        for line in self:
            # Only act on lines where your custom currency logic applies
            if line.currency_id and line.amount_currency and line.currency_id != line.company_id.currency_id:
                # Convert amount_currency to company currency
                company_currency = line.move_id.company_id.currency_id
                balance = company_currency._convert(
                    line.amount_currency,
                    line.currency_id,
                    line.move_id.company_id,
                    line.date or fields.Date.today(),
                    round=False,
                )
                line.with_context(skip_custom_balance=True).balance = balance
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._apply_custom_balance()  # safe call
        return lines

    def write(self, vals):
        if self.env.context.get('skip_custom_balance'):
            return super().write(vals)
        result = super().write(vals)
        if any(x in vals for x in ['amount_currency', 'currency_id']):
            # Recompute after write
            self._apply_custom_balance()
        return result

    # dics custom code add
    def _apply_custom_balance(self):
        for line in self:
            if (
                    self.env.context.get('skip_custom_balance')
                    or line.matched_debit_ids or line.matched_credit_ids
            ):
                continue
            if not self.env.context.get('skip_custom_balance'):
                # Only act on lines where your custom currency logic applies
                if line.currency_id and line.amount_currency and line.currency_id != line.company_id.currency_id:
                    company_currency = line.move_id.company_id.currency_id
                    balance = company_currency._convert(
                        line.amount_currency,
                        line.currency_id,
                        line.move_id.company_id,
                        line.date or fields.Date.today(),
                        round=False,
                    )
                    # write balance but avoid infinite recursion
                    line.with_context(skip_custom_balance=True).write({
                        'balance': balance
                    })
        return
