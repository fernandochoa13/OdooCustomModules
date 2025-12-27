# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from datetime import timedelta

class PMSInversionistas(models.Model):
    _name = "pms.investors"
    _description = "Investors Control"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference')
    partner_id = fields.Many2one('res.partner', string='Investor', required=True)
    project = fields.Many2one('pms.projects', string='Project Property', required=True)
    property_id = fields.Many2one('pms.property', related='project.address', readonly=True, store=True)
    project_status = fields.Selection(related='project.status_construction', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date = fields.Date(string='Date of Investment', required=True)
    capital_funds = fields.Float(string='Capital Funds', required=True)
    interest_rate = fields.Float(string='%ROI', digits=(3, 2), required=True)
    total_profit = fields.Float(compute='_compute_total_profit', string='Total Profit', store=True)
    total_amount = fields.Float(compute='_compute_total_profit', string='Total Amount', store=True)
    date_paid = fields.Date(string='Date Paid')
    liquidation_date = fields.Date(compute='_compute_liquidation_date', string='Liquidation Date', store=True, readonly=False)
    investment_type = fields.Selection([('new_investments', 'New Investments'), ('re_investments', 'Re Investments')], string='Investment Type', required=True)
    remarks_note = fields.Text(string='Remarks')
    projects_where_reinvested = fields.One2many('pms.reinvestments','investor', string='Projects Where Reinvested')


    status = fields.Selection([('draft', 'Draft'), ('invested', 'Invested'), ('liquidated', 'Liquidated')], string='Status', required=True, default='draft')

    # Payment
    payment_comments = fields.Text(string='Payment Comments')
    exit_strategy = fields.Selection([('liquidation', 'Liquidation'), ('reinvestment', 'Reinvestment'), ('partial', 'Partial')], string='Exit Strategy')
    pctg_principal_reinvested = fields.Float(string='% Principal Reinvested')
    pctg_profit_reinvested = fields.Float(string='% Profit Reinvested')

    @api.constrains('pctg_principal_reinvested', 'pctg_profit_reinvested')
    def pctg_principal(self):
        for rec in self:
            if rec.pctg_principal_reinvested > 100 or rec.pctg_profit_reinvested > 100:
                raise ValidationError("Sum of Principal and Profit Reinvested mustnt be more than 100%.")



    @api.constrains('interest_rate')
    def check_interest_rate(self):
        for rec in self:
            if rec.interest_rate < 0 or rec.interest_rate > 1:
                raise ValidationError("Interest rate must be between 0 and 1.")

    @api.depends('date')
    def _compute_liquidation_date(self):
        for rec in self:
            if rec.date != False:
                future_year = rec.date + timedelta(days=365)
                first = future_year.replace(day=1)
                rec.liquidation_date = first - timedelta(days=1)

    @api.depends('capital_funds', 'interest_rate')
    def _compute_total_profit(self):
        for rec in self:
            rec.total_profit = rec.capital_funds * rec.interest_rate
            rec.total_amount = rec.capital_funds + rec.total_profit
            

    def _get_report_base_filename(self):
        return f'Agreement {self.name}'


    def monthly_updates(self):
        pass
        # Open wizard to select template
        # 
        # Group by investor and for loop
        # Get data for investor
        # Send Email according to template

    def liquidation_mail(self):
        pass

    def send_contract(self):
        pass

    def action_invested(self):
        if self.investment_type == 'new_investments':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Invested Wizard',
                'res_model': 'pms.invested.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'investor': self.id, 'amount': self.capital_funds}
            }
        elif self.investment_type == 're_investments':
            self.status = 'invested'

    def action_liquidated(self):
        # Check liquidated fields are filled
        if not self.exit_strategy:
            raise UserError("Please select an exit strategy.")
        # Check is reinvesments if so, check pctg_principal_reinvested and pctg_profit_reinvested and propertyies to where re invested
        if self.exit_strategy == 'reinvestment' or self.exit_strategy == 'partial':
            if self.projects_where_reinvested == False:
                raise UserError("Please fill in the reinvestment fields.")
        # Open wizard
        return {
                'type': 'ir.actions.act_window',
                'name': 'liquidated Wizard',
                'res_model': 'pms.liquidated.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'investor': self.id, 'amount': self.capital_funds}
            }

class pmsliquidated_wizard(models.TransientModel):
    _name = 'pms.liquidated.wizard'
    _description = 'Invested Wizard'

    date = fields.Date(string='Date of Investment', required=True)
    remarks = fields.Text(string='Remarks')
    
    payment_journal = fields.Many2one('account.journal', string='Payment Journal', domain="[('type', 'in', ['cash', 'bank'])]")

    without_journal = fields.Boolean(string='Without Journal', default=False, help="Check this box if you want to create the entry without a journal.")

    def create_entry(self):
        
        record_id = self.env['pms.investors'].browse(self._context.get('investor'))
        amount = self._context.get('amount')

        if not record_id or not amount:
            raise UserError("Investor record or amount is missing.")
        
        # Create journal entry
        # Taking into account the exit strategy, interest
        
        record_id.status = 'liquidated'
        
        if not self.without_journal:
            if record_id.exit_strategy == 'liquidation':
                credit = {
                    'account_id': self.payment_journal.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                    'debit': 0,
                    'credit': record_id.total_amount,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                }

                debit_capital = {
                    'account_id': self.env['account.account'].search([('code', '=', '2000404'), ('company_id', '=', record_id.company_id.id)]).id,
                    'debit': record_id.capital_funds,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                }

                debit_interest = {
                    'account_id': self.env['account.account'].search([('code', '=', '6000404'), ('company_id', '=', record_id.company_id.id)]).id,
                    'debit': record_id.total_profit,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                }

                journal_entry = self.env['account.move'].sudo().create({
                'date': self.date,
                'company_id': record_id.company_id.id,
                'move_type': 'entry',
                'ref': f'Liquidation Entry {self.remarks}',
                'line_ids': [(0, 0, credit), (0, 0, debit_capital), (0, 0, debit_interest)], 
            })
                
            
            elif record_id.exit_strategy == 'reinvestment':
                line_ids = []
                for reinvestment in record_id.projects_where_reinvested:
                    credit = {
                        'account_id': self.env['account.account'].search([('code', '=', '2000404'), ('company_id', '=', record_id.company_id.id)]).id,
                        'debit': 0,
                        'credit': record_id.total_amount * (reinvestment.pctg_investments / 100),
                        'partner_id': record_id.partner_id.id,
                        'analytic_distribution': {str(reinvestment.project.address.analytical_account.id): 100.0},
                        'name': f'Investment Liquidation Entry {self.remarks}'
                    }

                    line_ids.append((0, 0, credit))

                    # Create new investor record with reinvestments
                    new_investor = self.env['pms.investors'].sudo().create({
                        'name': record_id.name,
                        'partner_id': record_id.partner_id.id,
                        'project': reinvestment.project.id,
                        'company_id': record_id.company_id.id,
                        'date': self.date,
                        'capital_funds': record_id.total_amount * (reinvestment.pctg_investments / 100),
                        'interest_rate': record_id.interest_rate,
                        'investment_type': 're_investments',
                        'status': 'invested'
                    })

                debit_capital = (0, 0, {
                    'account_id': self.env['account.account'].search([('code', '=', '2000404'), ('company_id', '=', record_id.company_id.id)]).id,
                    'debit': record_id.capital_funds,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                })

                line_ids.append(debit_capital)

                debit_interest = (0, 0, {
                    'account_id': self.env['account.account'].search([('code', '=', '6000404'), ('company_id', '=', record_id.company_id.id)]).id,
                    'debit': record_id.total_profit,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                })

                line_ids.append(debit_interest)

                journal_entry = self.env['account.move'].sudo().create({
                'date': self.date,
                'company_id': record_id.company_id.id,
                'move_type': 'entry',
                'ref': f'Liquidation Entry {self.remarks}',
                'line_ids': line_ids
                })

            
            elif record_id.exit_strategy == 'partial':
                line_ids = []

                for reinvestment in record_id.projects_where_reinvested:
                    credit = {
                        'account_id': self.env['account.account'].search([('code', '=', '2000404'), ('company_id', '=', record_id.company_id.id)]).id,
                        'debit': 0,
                        'credit': ((record_id.capital_funds * record_id.pctg_principal_reinvested) + (record_id.total_profit * record_id.pctg_profit_reinvested)) * (reinvestment.pctg_investments / 100),
                        'partner_id': record_id.partner_id.id,
                        'analytic_distribution': {str(reinvestment.project.address.analytical_account.id): 100.0},
                        'name': f'Investment Liquidation Entry {self.remarks}'
                    }

                    line_ids.append((0, 0, credit))
                    
                    new_investor = self.env['pms.investors'].sudo().create({
                        'name': record_id.name,
                        'partner_id': record_id.partner_id.id,
                        'project': reinvestment.project.id,
                        'company_id': record_id.company_id.id,
                        'date': self.date,
                        'capital_funds': ((record_id.capital_funds * record_id.pctg_principal_reinvested) + (record_id.total_profit * record_id.pctg_profit_reinvested)) * (reinvestment.pctg_investments / 100),
                        'interest_rate': record_id.interest_rate,
                        'investment_type': 're_investments',
                        'status': 'invested'
                    })

                payment = {
                    'account_id': self.payment_journal.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                    'debit': 0,
                    'credit': record_id.total_amount - ((record_id.capital_funds * record_id.pctg_principal_reinvested) + (record_id.total_profit * record_id.pctg_profit_reinvested)),
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                }

                line_ids.append((0, 0, payment))

                debit_capital = {
                    'account_id': self.env['account.account'].search([('code', '=', '2000404'), ('company_id', '=', record_id.company_id.id)]).id,
                    'debit': record_id.capital_funds,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                }

                line_ids.append((0, 0, debit_capital))

                debit_interest = {
                    'account_id': self.env['account.account'].search([('code', '=', '6000404'), ('company_id', '=', record_id.company_id.id)]).id,
                    'debit': record_id.total_profit,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Liquidation Entry {self.remarks}'
                }

                line_ids.append((0, 0, debit_interest))

                journal_entry = self.env['account.move'].sudo().create({
                'date': self.date,
                'company_id': record_id.company_id.id,
                'move_type': 'entry',
                'ref': f'Liquidation Entry {self.remarks}',
                'line_ids': line_ids
                })
            
            journal_entry.action_post()

class pmsinvested_wizard(models.TransientModel):
    _name = 'pms.invested.wizard'
    _description = 'Invested Wizard'

    date = fields.Date(string='Date of Investment', required=True)
    remarks = fields.Text(string='Remarks')
    company = fields.Many2one('res.company', string='Company', required=True)
    payment_journal = fields.Many2one('account.journal', string='Payment Journal', domain="[('type', 'in', ['cash', 'bank']), ('company_id', '=', company)]")

    without_journal = fields.Boolean(string='Without Journal', default=False, help="Check this box if you want to create the entry without a journal.")

    def create_entry(self):
        record_id = self.env['pms.investors'].browse(self._context.get('investor'))
        amount = self._context.get('amount')
        
        if not record_id or not amount:
            raise UserError("Investor record or amount is missing.")

        record_id.status = 'invested'
        record_id.company_id = self.company.id

        # Create journal entry
        
        if not self.without_journal:
            journal_entry = self.env['account.move'].sudo().create({
                'date': self.date,
                'company_id': self.company.id,
                'move_type': 'entry',
                'ref': f'Investment Entry {self.remarks}',
                'line_ids': [
                (0, 0, {
                    'account_id': self.payment_journal.inbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                    'debit': amount,
                    'credit': 0,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Entry {self.remarks}',
                }),
                (0, 0, {
                    'account_id': self.env['account.account'].search([('code', '=', '2000404'), ('company_id', '=', self.company.id)]).id,
                    'debit': 0,
                    'credit': amount,
                    'partner_id': record_id.partner_id.id,
                    'analytic_distribution': {str(record_id.project.address.analytical_account.id): 100.0},
                    'name': f'Investment Entry {self.remarks}',
                }),
                ],
            })

            # Post the journal entry
            journal_entry.action_post()


    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    


class pms_reinvestments(models.Model):
    _name = 'pms.reinvestments'
    _description = 'Reinvestments Table'

    investor = fields.Many2one('pms.investors', string='Investment', required=True)
    project = fields.Many2one('pms.projects', string='Project Property', required=True)
    pctg_investments = fields.Float(string='% Investments', required=True)

'''
    @api.constrains('investor', 'pctg_investments')
    def check_total_pctg_investments(self):
        for rec in self:
            total_pctg = sum(self.search([('investor', '=', rec.investor.id)]).mapped('pctg_investments'))
            if total_pctg > 100:
                raise ValidationError("Total percentage of investments for this investor must not exceed 100%.")

            elif total_pctg < 100:
                raise ValidationError("Total percentage of investments for this investor must be 100%.")
'''    
    
