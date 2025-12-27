# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError

class HrExpense(models.Model):
    _inherit = "hr.expense"

    billable = fields.Boolean(string="Billable")
    invoiced = fields.Many2one(comodel_name="account.move", string="Invoiced")
    markup = fields.Float(string="Markup")
    @api.onchange("billable")
    def _onchange_billable(self):
        if self.billable:
            self.markup = self.env['ir.config_parameter'].sudo().get_param('pms.markup')


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_payment_vals(self):
        self.ensure_one()
        payment_method_line = self.env['account.payment.method.line'].search(
            [('payment_type', '=', 'outbound'),
             ('journal_id', '=', self.bank_journal_id.id),
             ('code', '=', 'manual'),
             ('company_id', '=', self.company_id.id)], limit=1)
        if not payment_method_line:
            raise UserError(_("You need to add a manual payment method on the journal (%s)", self.bank_journal_id.name))

        if not self.expense_line_ids or self.is_multiple_currency:
            currency = self.company_id.currency_id
            amount = self.total_amount
        else:
            currency = self.expense_line_ids[0].currency_id
            amount = sum(self.expense_line_ids.mapped('total_amount'))
        move_lines = []
        for expense in self.expense_line_ids:
            expense_amount = expense.total_amount_company if self.is_multiple_currency else expense.total_amount
            tax_data = self.env['account.tax']._compute_taxes([
                expense._convert_to_tax_base_line_dict(price_unit=expense_amount, currency=currency)
            ])
            rate = abs(expense_amount / expense.total_amount_company)
            base_line_data, to_update = tax_data['base_lines_to_update'][0]  # Add base lines
            amount_currency = to_update['price_subtotal']
            expense_name = expense.name.split("\n")[0][:64]
            base_move_line = {
                'name': f'{expense.employee_id.name}: {expense_name}',
                'account_id': base_line_data['account'].id,
                'product_id': base_line_data['product'].id,
                'analytic_distribution': base_line_data['analytic_distribution'],
                'billable': expense.billable,
                'markup': expense.markup,
                'expense_id': expense.id,
                'tax_ids': [Command.set(expense.tax_ids.ids)],
                'tax_tag_ids': to_update['tax_tag_ids'],
                'amount_currency': amount_currency,
                'currency_id': currency.id,
            }
            move_lines.append(base_move_line)
            total_tax_line_balance = 0.0
            for tax_line_data in tax_data['tax_lines_to_add']:  # Add tax lines
                tax_line_balance = expense.currency_id.round(tax_line_data['tax_amount'] / rate)
                total_tax_line_balance += tax_line_balance
                tax_line = {
                    'name': self.env['account.tax'].browse(tax_line_data['tax_id']).name,
                    'account_id': tax_line_data['account_id'],
                    'analytic_distribution': tax_line_data['analytic_distribution'],
                    'expense_id': expense.id,
                    'tax_tag_ids': tax_line_data['tax_tag_ids'],
                    'balance': tax_line_balance,
                    'amount_currency': tax_line_data['tax_amount'],
                    'tax_base_amount': expense.currency_id.round(tax_line_data['base_amount'] / rate),
                    'currency_id': currency.id,
                    'tax_repartition_line_id': tax_line_data['tax_repartition_line_id'],
                }
                move_lines.append(tax_line)
            base_move_line['balance'] = expense.total_amount_company - total_tax_line_balance
        expense_name = self.name.split("\n")[0][:64]
        move_lines.append({  # Add outstanding payment line
            'name': f'{self.employee_id.name}: {expense_name}',
            'account_id': self.expense_line_ids[0]._get_expense_account_destination(),
            'balance': -self.total_amount,
            'amount_currency': currency.round(-amount),
            'currency_id': currency.id,
        })
        return {
            **self._prepare_move_vals(),
            'journal_id': self.bank_journal_id.id,
            'move_type': 'entry',
            'amount': amount,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'payment_method_line_id': payment_method_line.id,
            'currency_id': currency.id,
            'line_ids': [Command.create(line) for line in move_lines],
        }
