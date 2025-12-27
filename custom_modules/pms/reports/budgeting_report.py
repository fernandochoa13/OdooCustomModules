from odoo import api, models, tools, fields, _
from datetime import datetime, time, timedelta
from datetime import date
import base64
import io

from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning

# Make a budgeting report model just like the one below but in summary showing the total amount of money, of receipts and of payments

class budgeting_report_summary(models.Model):
    _name = 'budgeting.report.summary'
    _description = "Budgeting Report Summary"
    _auto = False

    id = fields.Integer(readonly=True)
    company = fields.Char(readonly=True)
    bank_name = fields.Char(readonly=True)
    banking_total_amount = fields.Float(readonly=True)
    banking_total_unmatched = fields.Float(readonly=True)
    banking_total_unmatched_all = fields.Float(readonly=True)

    @property
    def _table_query(self):
        return f"""
            SELECT
                sub4.id as id,
                sub4.bank_name as bank_name,
                sub4.company as company,
                sub4.banking_total_amount as banking_total_amount,
                -- Original logic: banking_total_unmatched + banking_total_amount for clear_budget = TRUE
                COALESCE(sub3.banking_total_unmatched, 0) + sub4.banking_total_amount as banking_total_unmatched,
                -- New field with original logic: banking_total_unmatched_all + banking_total_amount for all unmatched
                COALESCE(sub5.banking_total_unmatched_all, 0) + sub4.banking_total_amount as banking_total_unmatched_all

            FROM (
                -- sub4: Calculates the total banking amount from bank statement lines
                SELECT
                    aj.id as id,
                    aj.name as bank_name,
                    rc.name as company,
                    SUM(absl.amount) as banking_total_amount
                FROM account_bank_statement_line absl
                LEFT JOIN account_move am ON absl.move_id = am.id
                LEFT JOIN account_journal aj ON am.journal_id = aj.id
                LEFT JOIN res_company rc ON aj.company_id = rc.id
                WHERE aj.type = 'bank'
                GROUP BY aj.id, aj.name, rc.name
            ) sub4
            LEFT JOIN (
                -- sub3: Calculates the sum of unmatched amounts where account_move.clear_budget = TRUE
                SELECT
                    sub1.id as id,
                    SUM(sub1.banking_total_unmatched) as banking_total_unmatched
                FROM (
                    SELECT
                        sub2.id as id,
                        account_move_line.balance as banking_total_unmatched, -- Using balance directly
                        CASE
                            WHEN account_move.budget_date IS NULL THEN account_move.date
                            WHEN account_move.budget_date IS NOT NULL THEN account_move.budget_date
                        END AS date_value
                    FROM account_move_line
                    LEFT JOIN account_move ON account_move_line.move_id = account_move.id
                    LEFT JOIN account_journal ON account_move_line.journal_id = account_journal.id
                    INNER JOIN (
                        SELECT
                            aj_inner.id as id,
                            apml.payment_account_id as gl_account
                        FROM account_payment_method_line apml
                        INNER JOIN account_journal aj_inner ON apml.journal_id = aj_inner.id
                        WHERE apml.payment_account_id IS NOT NULL
                        AND aj_inner.type = 'bank'
                        GROUP BY aj_inner.id, apml.payment_account_id
                    ) sub2
                    ON account_move_line.account_id = sub2.gl_account
                    WHERE account_move_line.reconciled = 'False'
                    AND account_move_line.parent_state = 'posted'
                    AND account_move.clear_budget = TRUE -- Condition for the existing field
                ) sub1
                GROUP BY sub1.id
            ) sub3
            ON sub4.id = sub3.id
            LEFT JOIN (
                -- sub5: Calculates the sum of ALL unmatched amounts (clear_budget TRUE or FALSE)
                SELECT
                    sub6.id as id,
                    SUM(sub6.banking_total_unmatched) as banking_total_unmatched_all -- Renamed column for clarity
                FROM (
                    SELECT
                        sub7.id as id,
                        account_move_line.balance as banking_total_unmatched, -- Using balance directly
                        CASE
                            WHEN account_move.budget_date IS NULL THEN account_move.date
                            WHEN account_move.budget_date IS NOT NULL THEN account_move.budget_date
                        END AS date_value
                    FROM account_move_line
                    LEFT JOIN account_move ON account_move_line.move_id = account_move.id
                    LEFT JOIN account_journal ON account_move_line.journal_id = account_journal.id
                    INNER JOIN (
                        SELECT
                            aj_inner.id as id,
                            apml.payment_account_id as gl_account
                        FROM account_payment_method_line apml
                        INNER JOIN account_journal aj_inner ON apml.journal_id = aj_inner.id
                        WHERE apml.payment_account_id IS NOT NULL
                        AND aj_inner.type = 'bank'
                        GROUP BY aj_inner.id, apml.payment_account_id
                    ) sub7
                    ON account_move_line.account_id = sub7.gl_account
                    WHERE account_move_line.reconciled = 'False'
                    AND account_move_line.parent_state = 'posted'
                    -- Removed: AND account_move.clear_budget = TRUE (This subquery includes all unmatched)
                ) sub6
                GROUP BY sub6.id
            ) sub5
            ON sub4.id = sub5.id
        """

class budgeting_report(models.Model):
    _name = 'budgeting.report'
    _description = "operating budget"
    _auto = False
    _order = 'bank_date desc, cleared_state asc, transaction_type asc, journal_date desc, id desc' 

    id = fields.Integer(readonly=True)
    bank_date = fields.Date(readonly=True)
    journal_date = fields.Date(readonly=True)
    labell = fields.Char(string="Label", readonly=True)
    reference = fields.Char(readonly=True)
    partner = fields.Char(readonly=True)
    amount = fields.Float(readonly=True)
    running_balance = fields.Float(readonly=True)
    transaction_type = fields.Char(readonly=True)
    cleared_state = fields.Boolean(readonly=True)

    
    # account_payment payment_reference, con account_payment.move_id es id de am
    check_number = fields.Char(string="Check Number", readonly=True)


    #Button that open selected record
    def open_record(self):
        return {
            'type': 'ir.actions.act_window',
            'name': ('account.view_move_form'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.id,
        }

    def clear_records(self):
        for records in self:
            record = self.env['account.move'].browse(records.id)
            if record.clear_budget:
                record.clear_budget = False
            else:
                record.clear_budget = True

    def set_budget_date(self):
        ctx = dict(
            active_ids=self.ids
            )
        
        budget_date_form = self.env.ref('pms.budget_date_wizard_form')
        return {
                'name': 'Budget Date Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'budget.date.wizard',
                'views': [(budget_date_form.id, 'form')],
                'view_id': budget_date_form.id,
                'target': 'new',
                'context': ctx}

    def return_draft(self):
        for records in self:
            if records.transaction_type == 'Banking':
                raise UserError('Only Unmatched records can be returned to draft')
            else:
                record = self.env['account.move'].browse(records.id)
                record.button_draft()

    def cancel_records(self):
        for records in self:
            if records.transaction_type == 'Draft':
                record = self.env['account.move'].browse(records.id)
                record.button_cancel()
            else:
                raise UserError('Only draft records can be cancelled')

    def action_open_reconcile(self):
        """Open the bank reconciliation widget for the journal in context."""
        journal_id = self.env.context.get('journal_id')
        
        if not journal_id:
            raise UserError(_("No journal selected. Please select a journal first."))
        
        journal = self.env['account.journal'].browse(journal_id)
        
        if not journal.exists():
            raise UserError(_("Journal not found."))
        
        if journal.type not in ('bank', 'cash'):
            raise UserError(_("Reconciliation is only available for bank and cash journals."))
        
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'default_journal_id': journal_id,
                'search_default_journal_id': journal_id,
                'search_default_not_matched': True,
            },
        )

    @property
    def _table_query(self):
        journal_id = self.env.context.get('journal_id')
        account_tuple: list = self.env.context.get('account_tuple')
        if len(account_tuple) > 1:
            accounts_outstanding = tuple(account_tuple)
        elif len(account_tuple) == 1:
            accounts_outstanding = f"({account_tuple[0]})"




        return f"""
                SELECT sub.*, sum(sub.amount) over (order by sub.bank_date asc, sub.cleared_state desc NULLS LAST, transaction_type desc, journal_date asc, id asc) as running_balance

                FROM (
                    SELECT 
                        account_move.id as id, 
                        account_move.clear_budget as cleared_state, 
                        account_move.date as journal_date, 
                        account_move.date as bank_date, 
                        account_bank_statement_line.payment_ref as reference, 
                        account_bank_statement_line.payment_ref as labell, 
                        res_partner.name as partner, 
                        account_bank_statement_line.amount as amount, 
                        'Banking' as transaction_type,
                        'Not Available' AS check_number

                        FROM account_bank_statement_line

                        LEFT JOIN account_move ON account_bank_statement_line.move_id = account_move.id

                        LEFT JOIN res_partner ON account_bank_statement_line.partner_id = res_partner.id

                WHERE account_move.journal_id = {journal_id}

                UNION ALL
                (
                SELECT 
                    account_move_line.move_id AS id, 
                    account_move.clear_budget as cleared_state,
                    CASE 
                        WHEN account_move.budget_date IS NULL THEN account_move.date
					    WHEN account_move.budget_date IS NOT NULL THEN account_move.budget_date
				    END AS journal_date,
                    null as bank_date, 
                    account_move_line.name as labell, 
                    account_move.ref as reference, 
                    res_partner.name as partner, 
                    SUM(account_move_line.balance) as amount,
                    CASE 
                        WHEN account_move_line.parent_state = 'draft' THEN 'Draft' 
                        WHEN account_move_line.parent_state = 'posted' THEN 'Unmatched'
                    END as transaction_type,
                    account_payment.check_number AS check_number

                        FROM account_move_line

                        LEFT JOIN res_partner ON account_move_line.partner_id = res_partner.id

                LEFT JOIN account_move ON account_move_line.move_id = account_move.id
                LEFT JOIN account_bank_statement_line ON account_move.id = account_bank_statement_line.move_id
                
                LEFT JOIN account_payment ON account_move.id = account_payment.move_id

                        WHERE account_move_line.account_id IN {accounts_outstanding} AND account_move_line.reconciled = False AND account_move_line.parent_state IN ('draft', 'posted') AND account_bank_statement_line.id IS NULL AND COALESCE(account_move.budget_date, account_move.date) >= '2024-02-01'

                GROUP BY 
                    account_move_line.move_id, 
                    account_move.ref, 
                    account_move.clear_budget, 
                    account_move.budget_date, 
                    account_move.date, 
                    account_move_line.name, 
                    res_partner.name,
                    account_move_line.parent_state, 
                    account_payment.check_number
                )) sub

                ORDER BY sub.bank_date desc,
                sub.cleared_state asc NULLS FIRST,
                sub.transaction_type asc,
                sub.journal_date desc,
                sub.id desc
            """

class budgeting_report_wizard(models.TransientModel):
    _name = 'budgeting.report.wizard'
    _description = 'Budget Report Wizard'

    journal_id = fields.Many2one('account.journal', string='Bank to view Budget', domain="[('type', 'in', ['bank', 'cash'])]")

    def open_report(self):
        if self.journal_id:
            ctx = {"journal_id": self.journal_id.id, "account_tuple": self.env["account.payment.method.line"].search([('journal_id', '=', self.journal_id.id)]).mapped('payment_account_id').ids}
            return {
                'type': 'ir.actions.act_window',
                'name': 'budgeting.report.tree',
                'res_model': 'budgeting.report',
                'view_mode': 'tree',
                'context': ctx,
            }
