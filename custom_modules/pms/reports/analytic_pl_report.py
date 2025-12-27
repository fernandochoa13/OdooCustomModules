from odoo import fields, models, tools

class AccountAnalyticPnlReport(models.Model):
    _name = 'account.analytic.pnl.report'
    _description = 'Analytic P&L Report'
    _auto = False

    name = fields.Char(string='Description', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    general_account_id = fields.Many2one('account.account', string='Financial Account', readonly=True)
    account_type = fields.Selection([
        ('1_income', 'Income'),
        ('2_income_other', 'Other Income'),
        ('4_expense', 'Expenses'),
        ('5_expense_depreciation', 'Depreciation'),
        ('3_expense_direct_cost', 'Cost of Revenue'),
        ('6_other', 'Other'),
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
        Drops and recreates the SQL view for the Analytic P&L Report.
        This view is filtered to include only P&L-related account types.
        """
        tools.drop_view_if_exists(self.env.cr, 'account_analytic_pnl_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW account_analytic_pnl_report AS (
            SELECT
                aal.id as id,
                aal.name,
                aal.date,
                abs(aal.amount) as amount,
                aal.account_id as analytic_account_id,
                aal.general_account_id as general_account_id,
                CASE
                    WHEN aa.account_type = 'income' THEN '1_income'
                    WHEN aa.account_type = 'income_other' THEN '2_income_other'
                    WHEN aa.account_type = 'expense' THEN '4_expense'
                    WHEN aa.account_type = 'expense_depreciation' THEN '5_expense_depreciation'
                    WHEN aa.account_type = 'expense_direct_cost' THEN '3_expense_direct_cost'
                    ELSE '6_other'
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
                aa.account_type IN ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')
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