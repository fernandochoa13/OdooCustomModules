# models/analytic_report.py
from odoo import fields, models, tools

class AccountAnalyticLineReport(models.Model):
    _name = 'account.analytic.line.report'
    _description = 'Analytic Report by Account Type (Corrected)'
    _auto = False

    name = fields.Char(string='Description', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    account_type = fields.Selection([
        ('asset_receivable', 'Receivable'),
        ('asset_cash', 'Bank and Cash'),
        ('asset_current', 'Current Assets'),
        ('asset_non_current', 'Non-current Assets'),
        ('asset_prepayments', 'Prepayments'),
        ('asset_fixed', 'Fixed Assets'),
        ('liability_payable', 'Payable'),
        ('liability_credit_card', 'Credit Card'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        ('equity', 'Equity'),
        ('equity_unaffected', 'Current Year Earnings'),
        ('income', 'Income'),
        ('income_other', 'Other Income'),
        ('expense', 'Expenses'),
        ('expense_depreciation', 'Depreciation'),
        ('expense_direct_cost', 'Cost of Revenue'),
        ('off_balance', 'Off-Balance Sheet'),
    ], string='Account Type', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True, store=True)

    def init(self):
        """
        Drops and recreates the SQL view for the Analytic Report to avoid column definition errors.
        """
        tools.drop_view_if_exists(self.env.cr, 'account_analytic_line_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW account_analytic_line_report AS (
                SELECT
                    aal.id as id,
                    aal.name,
                    aal.date,
                    aal.amount,
                    aal.account_id as analytic_account_id,
                    aa.account_type as account_type,
                    aal.company_id
                FROM
                    account_analytic_line aal
                LEFT JOIN
                    account_account aa ON aal.general_account_id = aa.id
            )
        """)