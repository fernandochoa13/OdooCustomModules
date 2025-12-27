from odoo import fields, models, tools, api
from datetime import date


# access_account_analytic_cash_pnl_report,access.account.analytic.cash.pnl.report,model_account_analytic_cash_pnl_report,base.group_user,1,1,1,1
# access_cash_pnl_report_wizard,access_account_analytic_cash_pnl_report,model_cash_pnl_report_wizard,base.group_user,1,1,1,1


# access_account_analytic_cash_bs_report,access.account.analytic.cash.bs.report,model_account_analytic_cash_bs_report,base.group_user,1,1,1,1
# access_cash_bs_report_wizard,access_account_analytic_cash_bs_report,model_cash_bs_report_wizard,base.group_user,1,1,1,1


class CashbsReportWizard(models.TransientModel):
    _name = 'cash.bs.report.wizard'
    _description = 'Cash Balance Sheet Report Wizard'

    year = fields.Selection(
        selection=[('2023', '2023'), ('2024', '2024'), ('2025', '2025'), ('2026', '2026')],
        string='Year',
        required=True,
        default=lambda self: str(date.today().year)
    )

    def action_open_report(self):
        """
        Action to open the Cash P&L report, passing the selected year in the context.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.cash.bs.report',
            'view_mode': 'pivot,tree',
            'name': 'Analytic Cash Basis Balance Sheet Report',
            'context': {
                'cash_bs_year': self.year,
            },
        }


class AccountAnalyticCashbsReport(models.Model):
    _name = 'account.analytic.cash.bs.report'
    _description = 'Analytic P&L Report Cash'
    _auto = False

    name = fields.Char(string='Description', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    accrual_date = fields.Date(string="Accrual Date", readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    general_account_id = fields.Many2one('account.account', string='Financial Account', readonly=True)
    account_type = fields.Selection([
        ('1a_asset_cash', 'Bank and Cash'),
        ('1b_asset_receivable', 'Receivable'),
        ('1c_asset_current', 'Current Assets'),
        ('1d_asset_prepayments', 'Prepayments'),
        ('1e_asset_fixed', 'Fixed Assets'),
        ('1f_asset_non_current', 'Non-current Assets'),
        ('1g_liability_current', 'Current Liabilities'),
        ('1h_liability_payable', 'Payable'),
        ('1i_liability_non_current', 'Non-current Liabilities'),
        ('1j_liability_credit_card', 'Credit Card'),
        ('1k_equity', 'Equity'),
        ('1l_equity_unaffected', 'Current Year Earnings'),
        ('1m_off_balance', 'Off-Balance Sheet'),
        ('1n_other', 'Other')
    ], string='Account Type', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True, store=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

    def action_view_move(self):
        """
        Opens the corresponding account.move record for the selected report line.
        """
        self.ensure_one()
        if self.move_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
                'target': 'current',
                'name': self.move_id.name,
            }
        return False

    @property
    def _table_query(self):
        """
        Drops and recreates the SQL view for the Analytic P&L Report.
        This view is filtered to include only P&L-related account types.
        """
        tools.drop_view_if_exists(self.env.cr, 'account_analytic_cash_bs_report')
        
        active_company_id = self.env.company.id
        # Get the year from the context, or default to the current year
        selected_year = self.env.context.get('cash_bs_year', date.today().year)
        
        # # Build the date filter for the main query
        # date_filter = f"aml.date BETWEEN '{selected_year}-01-01' AND '{selected_year}-12-31'"
        
        
        return f"""
            SELECT
                aal.id as id,
                aal.name,
                aal.date as accrual_date,
                am.cash_date as date,
                CASE
                    WHEN aa.account_type = 'income' THEN -aml.balance
                    WHEN aa.account_type = 'income_other' THEN -aml.balance 
                    WHEN aa.account_type = 'expense' THEN aml.balance
                    WHEN aa.account_type = 'expense_depreciation' THEN aml.balance
                    WHEN aa.account_type = 'expense_direct_cost' THEN aml.balance
                    ELSE -aml.balance
                END as amount,
                aal.account_id as analytic_account_id,
                aal.general_account_id as general_account_id,
                CASE
                    WHEN aa.account_type = 'asset_cash' THEN '1a_asset_cash'
                    WHEN aa.account_type = 'asset_receivable' THEN '1b_asset_receivable'
                    WHEN aa.account_type = 'asset_current' THEN '1c_asset_current'
                    WHEN aa.account_type = 'asset_prepayments' THEN '1d_asset_prepayments'
                    WHEN aa.account_type = 'asset_fixed' THEN '1e_asset_fixed'
                    WHEN aa.account_type = 'asset_non_current' THEN '1f_asset_non_current'
                    WHEN aa.account_type = 'liability_current' THEN '1g_liability_current'
                    WHEN aa.account_type = 'liability_payable' THEN '1h_liability_payable'
                    WHEN aa.account_type = 'liability_non_current' THEN '1i_liability_non_current'
                    WHEN aa.account_type = 'liability_credit_card' THEN '1j_liability_credit_card'
                    WHEN aa.account_type = 'equity' THEN '1k_equity'
                    WHEN aa.account_type = 'equity_unaffected' THEN '1l_equity_unaffected'
                    WHEN aa.account_type = 'off_balance' THEN '1m_off_balance'
                    ELSE '1n_other'
                END as account_type,
                aal.company_id,
                aal.currency_id,
                aml.move_id as move_id
            FROM
                account_analytic_line aal
            LEFT JOIN
                account_account aa ON aal.general_account_id = aa.id
            RIGHT JOIN
                cash_basis_temp_account_move_line aml ON aal.move_line_id = aml.id
            LEFT JOIN
                account_move am ON aml.move_id = am.id
            WHERE
                aa.account_type IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')
                AND (am.partial = false or am.partial is null) AND am.cash_date BETWEEN '{selected_year}-01-01' AND '{selected_year}-12-31'
                AND am.company_id = {active_company_id} 
            
        """        
    #             part.amount / ABS(sub_aml.total_per_account)
    #             FROM account_partial_reconcile part
    #             JOIN ONLY account_move_line aml ON aml.id = part.debit_move_id OR aml.id = part.credit_move_id
    #             JOIN ONLY account_move_line aml2 ON
    #                 (aml2.id = part.credit_move_id OR aml2.id = part.debit_move_id)
    #                 AND aml.id != aml2.id
        
                # hacer un join y si aml.partial = True, como en el query de arriba que busca en account_artial_reconcile, buscar los pagos de ese invoice en account_partial_reconcile
                # y luego tengo que poner esos pagos con esas fechas y esos montos de los pagos reemplazando la linea que tiene partial true
                # es decir los que tienen partial true no van a estar en el reporte, si no que se sacan de account_partial_reconcile
                # pero con el account_id del original
        
        # self.env.cr.execute(f"""
        #     CREATE OR REPLACE VIEW account_analytic_cash_pnl_report AS (
        #     SELECT
        #         aal.id as id,
        #         aal.name,
        #         aal.date as accrual_date,
        #         CASE
        #             WHEN am.cash_date IS NOT NULL THEN am.cash_date
        #             ELSE aml.date
        #         END as date,
        #         ABS(aml.balance) as amount,
        #         aal.amount as accrual_amount,
        #         aal.account_id as analytic_account_id,
        #         aal.general_account_id as general_account_id,
        #         CASE
        #             WHEN aa.account_type = 'income' THEN '1_income'
        #             WHEN aa.account_type = 'income_other' THEN '2_income_other'
        #             WHEN aa.account_type = 'expense' THEN '4_expense'
        #             WHEN aa.account_type = 'expense_depreciation' THEN '5_expense_depreciation'
        #             WHEN aa.account_type = 'expense_direct_cost' THEN '3_expense_direct_cost'
        #             ELSE '6_other'
        #         END as account_type,
        #         aal.company_id,
        #         aal.currency_id,
        #         aml.move_id as move_id
        #     FROM
        #         account_analytic_line aal
        #     LEFT JOIN
        #         account_account aa ON aal.general_account_id = aa.id
        #     LEFT JOIN
        #         account_move_line aml ON aal.move_line_id = aml.id
        #     WHERE
        #         aa.account_type IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')
        #     )
        # """)
        
        
        
            #  AND
            #     {date_filter}

    # def action_view_journal_items(self):
    #     """
    #     Opens a view of all journal items related to the selected analytic accounts.
    #     """
    #     # Get the IDs of all selected records from the context
    #     active_ids = self.env.context.get('active_ids', [])
        
    #     if not active_ids:
    #         return False

    #     # Get the analytic account IDs from the selected report records
    #     # Use self.browse(active_ids) to create a recordset from the list of IDs
    #     selected_records = self.env['account.analytic.pnl.report'].browse(active_ids)
    #     analytic_account_ids = selected_records.mapped('analytic_account_id').ids
        
    #     # Find all analytic lines that correspond to these analytic accounts and have a move_line_id
    #     analytic_lines = self.env['account.analytic.line'].search([
    #         ('account_id', 'in', analytic_account_ids),
    #         ('move_line_id', '!=', False)
    #     ])
        
    #     # Get the unique journal item IDs from the analytic lines
    #     move_line_ids = analytic_lines.mapped('move_line_id').ids

    #     # Return the action to open the journal items view
    #     return {
    #         'name': 'Journal Items',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'account.move.line',
    #         'view_mode': 'tree,form',
    #         'domain': [('id', 'in', move_line_ids)],
    #     }