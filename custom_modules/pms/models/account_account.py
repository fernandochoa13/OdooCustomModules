from odoo import api, fields, models, _


class AccountAccount(models.Model):
    _inherit = "account.account"

    reconcile = fields.Boolean(
        string='Allow Reconciliation',
        compute='_compute_reconcile',
        store=True,
        readonly=False,
        help="Check this box if this account allows reconciliation of journal items."
    )

    @api.depends('account_type', 'internal_group')
    def _compute_reconcile(self):
        """Override to allow reconciliation for credit card accounts."""
        for account in self:
            # Allow reconciliation for various account types including credit cards
            if account.account_type in (
                'asset_receivable',
                'liability_payable',
                'asset_current',
                'asset_cash',
                'liability_current',
                'liability_credit_card'  # Credit card accounts
            ):
                # Don't change if already set, just ensure it's available
                if not account.reconcile:
                    account.reconcile = False
            else:
                account.reconcile = False

    def action_open_reconcile(self):
        """Override to open bank reconciliation widget for bank/cash/credit card accounts."""
        self.ensure_one()
        
        # Check if this account is used by a bank, cash, or credit card journal
        financial_journals = self.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash', 'general')),
            ('default_account_id', '=', self.id)
        ], limit=1)
        
        # Use bank reconciliation widget for bank/cash/credit card accounts
        if financial_journals and self.account_type in ('asset_cash', 'asset_current', 'liability_current', 'liability_credit_card'):
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                default_context={
                    'default_journal_id': financial_journals.id,
                    'search_default_journal_id': financial_journals.id,
                    'search_default_not_matched': True,
                },
            )
        else:
            # Use standard reconciliation for other accounts
            action_context = {'show_mode_selector': False, 'mode': 'accounts', 'account_ids': [self.id,]}
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }

