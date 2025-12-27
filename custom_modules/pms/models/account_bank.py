from odoo import api, fields, models, _, Command

class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    amlsbudget_widget = fields.Binary(
        compute='_compute_budget_widget',
        readonly=False,
    )

    product_id = fields.Many2one('product.product', string='Product')

    @api.depends('st_line_id')
    def _compute_budget_widget(self):
        for wizard in self:
            st_line = wizard.st_line_id

            context = {
                'search_view_ref': 'pms.view_account_move_line_search_budget_matching',
                'tree_view_ref': 'pms.view_budget_widget_tree',
            }

            if wizard.partner_id:
                context['search_default_partner_id'] = wizard.partner_id.id

            dynamic_filters = []

            # == Dynamic Customer/Vendor filter ==
            journal = st_line.journal_id
            account_ids = set()

            inbound_accounts = journal._get_journal_inbound_outstanding_payment_accounts() - journal.default_account_id
            outbound_accounts = journal._get_journal_outbound_outstanding_payment_accounts() - journal.default_account_id

            # Matching on debit account.
            for account in inbound_accounts:
                account_ids.add(account.id)

            # Matching on credit account.
            for account in outbound_accounts:
                account_ids.add(account.id)

            cleared_filter = {
                'name': 'cleared_filter',
                'description': _("Cleared Transactions"),
                'domain': [('move_id.clear_budget', '=', True)],
                'is_default': True,
            }

            uncleared_filter = {
                'name': 'uncleared_filter',
                'description': _("Uncleard Transactions"),
                'domain': [('move_id.clear_budget', '=', False)],
                'is_default': False,
            }
            dynamic_filters.extend([cleared_filter, uncleared_filter])

            # Stringify the domain.
            for dynamic_filter in dynamic_filters:
                dynamic_filter['domain'] = str(dynamic_filter['domain'])


            domain_to_use = [
            # Base domain.
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('parent_state', '=', 'posted'),
            # Reconciliation domain.
            ('reconciled', '=', False),
            # Only unmatched
            ('account_id', 'in', tuple(account_ids)),
            # Special domain for statement lines.
            ('statement_line_id', '!=', self.id),
        ]

            wizard.amlsbudget_widget = {
                'domain': domain_to_use,

                'dynamic_filters': dynamic_filters,

                'context': context,
            }



    
    def button_validate(self, async_action=False):
        self.ensure_one()
 
        if self.state != 'valid':
            self.next_action_todo = {'type': 'move_to_next'}
            return

        partners = (self.line_ids.filtered(lambda x: x.flag != 'liquidity')).partner_id
        partner_id_to_set = partners.id if len(partners) == 1 else None

        to_reconcile = []
        line_ids_create_command_list = []
        aml_to_exchange_diff_vals = {}

        for i, line in enumerate(self.line_ids):
            if line.flag == 'exchange_diff':
                continue

            amount_currency = line.amount_currency
            balance = line.balance
            if line.flag == 'new_aml':
                to_reconcile.append((i, line.source_aml_id.id))
                exchange_diff = self.line_ids \
                    .filtered(lambda x: x.flag == 'exchange_diff' and x.source_aml_id == line.source_aml_id)
                if exchange_diff:
                    aml_to_exchange_diff_vals[i] = {
                        'amount_residual': exchange_diff.balance,
                        'amount_residual_currency': exchange_diff.amount_currency
                    }
                    amount_currency += exchange_diff.amount_currency
                    balance += exchange_diff.balance

            if line.account_id.id:
                line_ids_create_command_list.append(Command.create({
                    'name': line.name,
                    'sequence': i,
                    'account_id': line.account_id.id,
                    'product_id': line.product_id.id,
                    'partner_id': partner_id_to_set if line.flag in ('liquidity', 'auto_balance') else line.partner_id.id,
                    'currency_id': line.currency_id.id,
                    'amount_currency': amount_currency,
                    'balance': balance,
                    'reconcile_model_id': line.reconcile_model_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'tax_repartition_line_id': line.tax_repartition_line_id.id,
                    'tax_ids': [Command.set(line.tax_ids.ids)],
                    'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                    'group_tax_id': line.group_tax_id.id,
                }))
            else:
                line_ids_create_command_list.append(Command.create({
                    'name': line.name,
                    'sequence': i,
                    'account_id': line.account_id.id,
                    'partner_id': partner_id_to_set if line.flag in ('liquidity', 'auto_balance') else line.partner_id.id,
                    'currency_id': line.currency_id.id,
                    'amount_currency': amount_currency,
                    'balance': balance,
                    'reconcile_model_id': line.reconcile_model_id.id,
                    'analytic_distribution': line.analytic_distribution,
                    'tax_repartition_line_id': line.tax_repartition_line_id.id,
                    'tax_ids': [Command.set(line.tax_ids.ids)],
                    'tax_tag_ids': [Command.set(line.tax_tag_ids.ids)],
                    'group_tax_id': line.group_tax_id.id,
                }))
 
        self.js_action_reconcile_st_line(
            self.st_line_id.id,
            {
                'command_list': line_ids_create_command_list,
                'to_reconcile': to_reconcile,
                'exchange_diff': aml_to_exchange_diff_vals,
                'partner_id': partner_id_to_set,
            },
        )
        self.next_action_todo = {'type': 'reconcile_st_line'}

    @api.onchange('product_id')
    def _onchange_form_product_id(self):
        line = self._lines_widget_get_line_in_edit_form()
        if not line:
            return

        self._lines_widget_form_turn_auto_balance_into_manual_line(line)
        if self.product_id:
            line.product_id = self.product_id.id


    
class BankRecWidgetLine(models.Model):
    _inherit = "bank.rec.widget.line"

    product_id = fields.Many2one('product.product', string='Product', compute='_compute_product_id', store=True)

    @api.depends('source_aml_id')
    def _compute_product_id(self):
        for line in self:
            if line.flag in ('aml', 'new_aml', 'liquidity', 'exchange_diff'):
                line.product_id = line.source_aml_id.product_id.id
            else:
                line.product_id = line.product_id.id

    



