from odoo import fields, models, tools

# access_account_analytic_line_report,access.account.analytic.line.report,model_account_analytic_line_report,base.group_user,1,1,1,1

class AccountAnalyticBsReport(models.Model):
    _name = 'account.analytic.bs.report'
    _description = 'Analytic Balance Sheet Report'
    _auto = False

    name = fields.Char(string='Description', readonly=True)
    date = fields.Date(string='Date', readonly=True)
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
    
    def init(self):
        """
        Drops and recreates the SQL view for the Analytic Balance Sheet Report.
        This view is filtered to include only Balance Sheet-related account types.
        """
        tools.drop_view_if_exists(self.env.cr, 'account_analytic_bs_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW account_analytic_bs_report AS (
            SELECT
                aal.id as id,
                aal.name,
                aal.date,
                abs(aal.amount) as amount,
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
            LEFT JOIN
                account_move_line aml ON aal.move_line_id = aml.id
            WHERE
                aa.account_type IN (
                'asset_cash', 'asset_receivable', 'asset_current',
                'asset_prepayments', 'asset_fixed', 'asset_non_current',
                'liability_current', 'liability_payable', 'liability_non_current',
                'liability_credit_card', 'equity', 'equity_unaffected'
                )
            )
        """)
    
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
    #     selected_records = self.env['account.analytic.bs.report'].browse(active_ids)
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