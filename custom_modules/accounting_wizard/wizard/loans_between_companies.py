
from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
import ast
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache
import requests
import json
#from intuitlib.exceptions import AuthClientError

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict
import math
import re
import string


class LoansBetweenCompanies(models.TransientModel):
    _name = "loans.between.companies"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Loans Between Companies"

    #First Wizard
    company_disbursement = fields.Many2one('res.company', string='Company Disbursement')
    transaction_type = fields.Selection([('withdrawal', 'Withdrawal'), ('deposit', 'Deposit')], string='Transaction Type', default='withdrawal', store=True)
    date = fields.Date(string='Date')
    supplier = fields.Many2one('res.partner', string='Supplier')
    loan_amount = fields.Float(string='Loan Amount')
    loan_account = fields.Many2one('account.account', string='Loan Account')
    account_bank = fields.Many2one('account.account', string='Bank Account')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    reference = fields.Char(string='Reference')
    notes = fields.Text(string='Notes')
    #Second Wizard
    company = fields.Many2one('res.company', string='Company')
    account = fields.Many2one('account.account', string='Account')
    product = fields.Many2one('product.product', string='Product')
    label = fields.Char(string='Label')
    billable = fields.Boolean(string='Billable', default=False)
    markup = fields.Float(string='Markup')
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account')
    account_loan = fields.Many2one('account.account', string='Loan Account')
    amount = fields.Float(string='Amount')

    second_wizard = fields.Many2one('lbc.second.wizard', string='Second Wizard')

    def check_first_wizard_fields(self):
        if not self.company_disbursement or not self.transaction_type or not self.date or \
                not self.supplier or self.loan_amount <= 0 or not self.loan_account or \
                not self.account_bank:
            raise ValidationError("Please fill all fields.")

    def next(self):
         self.check_first_wizard_fields()
         second_wizard = self.env.ref('accounting_wizard.view_lbc_second_wizard_form')
         attachments_ids = self.attachment_ids.ids
         
         return {
            'name': 'Loans Between Companies Wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'lbc.second.wizard',
            'views': [(second_wizard.id, 'form')],
            'view_id': second_wizard.id,
            'target': 'new',
            'context': {
                    'default_company_disbursement': self.company_disbursement.id,
                    'default_transaction_type': self.transaction_type,
                    'default_supplier': self.supplier.id, 
                    'default_loan_amount': round(self.loan_amount, 2),
                    'default_loan_account': self.loan_account.id,
                    'default_account_bank': self.account_bank.id,
                    'default_date': self.date,
                    'default_reference': self.reference,
                    'default_notes': self.notes,
                    'default_attachment_ids': attachments_ids,
            }
        }

class LBCSecondWizard(models.TransientModel):
    _name = "lbc.second.wizard"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Loans Between Companies Wizard"

    second_wizard_data = fields.One2many('loans.between.companies', 'second_wizard', string='Second Wizard Data')

    def _create_header_company_disbursement(self):
        date = self._context.get('default_date')
        reference = self._context.get('default_reference')
        company_disbursement = self._context.get('default_company_disbursement')
        supplier = self._context.get('default_supplier')
        account_bank = self._context.get('default_account_bank')
        loan_amount = self._context.get('default_loan_amount')
        transaction_type = self._context.get('default_transaction_type')

        if transaction_type == 'withdrawal':
            header =  {
                'move_type': 'entry',
                'date': date,
                'budget_date': date,
                'ref': reference,
                'line_ids': [(0, 0, {
                            'name':'Loan',
                            'credit': loan_amount,
                            'account_id':account_bank,
                            'partner_id': supplier,
                        })],
                'company_id': company_disbursement,
            }
            return header
        elif transaction_type == 'deposit':
            header =  {
                'move_type': 'entry',
                'date': date,
                'budget_date': date,
                'ref': reference,
                'line_ids': [(0, 0, {
                            'name':'Loan',
                            'credit': 0.0,
                            'debit': loan_amount,
                            'account_id':account_bank,
                            'partner_id': supplier,
                        })],
                'company_id': company_disbursement,
            }
            return header

    
    def _create_line_company_disbursement(self, x):
        account_loan = self._context.get('default_loan_account')
        transaction_type = self._context.get('default_transaction_type')

        if transaction_type == 'withdrawal':
            lines = {
                'account_id': account_loan,
                'partner_id': x.company.partner_id.id,
                'name': x.label,
                'debit': round(x.amount, 2),
                'credit': 0.0,
            }
            return lines
        elif transaction_type == 'deposit':
            lines = {
                'account_id': account_loan,
                'partner_id': x.company.partner_id.id,
                'name': x.label,
                'debit': 0.0,
                'credit':round(x.amount, 2),
            }
            return lines

    
    def _create_header_company_loaning(self):
        date = self._context.get('default_date')
        reference = self._context.get('default_reference')
        attachments = self._context.get('default_attachment_ids')
        company_disbursement = self._context.get('default_company_disbursement')
        supplier = self._context.get('default_supplier')
        transaction_type = self._context.get('default_transaction_type')
        notes = self._context.get('default_notes')

        if transaction_type == 'withdrawal':
            
            for x in self.second_wizard_data.company:
                header =  {
                    'move_type': 'entry',
                    'invoice_date': date,
                    'date': date,
                    'budget_date': date,
                    'ref': reference,
                    'line_ids': [],
                    'company_id': x.id,
                }
                company_lines = self.second_wizard_data.filtered_domain([('company', '=', x.id)])
                partner = self.env['res.company'].browse(company_disbursement)
                credit = {
                    'account_id': company_lines.account_loan.id,
                    'partner_id': partner.partner_id.id,
                    'name': 'Loan',
                    'debit': 0.0,
                    'credit': round(sum(company_lines.mapped('amount')), 2),
                }
                lines = []
                lines.append(Command.create(credit))
                for y in company_lines:
                    if y.analytic_account:
                        loan_lines = {
                            'account_id': y.account.id,
                            'product_id': y.product.id,
                            'analytic_distribution': {str(y.analytic_account.id): 100.0},
                            'partner_id': supplier,
                            'name': y.label,
                            'billable': y.billable,
                            'markup': y.markup,
                            'debit': round(y.amount, 2),
                            'credit':0.0,
                        }
                        lines.append(Command.create(loan_lines))
                    else:
                        loan_lines = {
                            'account_id': y.account.id,
                            'product_id': y.product.id,
                            'partner_id': supplier,
                            'name': y.label,
                            'billable': y.billable,
                            'markup': y.markup,
                            'debit': round(y.amount, 2),
                            'credit':0.0,
                        }
                        lines.append(Command.create(loan_lines))
                header['line_ids'] += lines
                journal_entry_loaning = self.env['account.move'].with_company(x).create(header)
                journal_entry_loaning.action_post()
                journal_entry_loaning.message_post(body=notes)
                attachment_loaning = self.env["ir.attachment"]
                for attachment_id in attachments:
                    attachment_loaning = attachment_loaning.browse(attachment_id)
                    attachment_loaning.copy({'res_id': journal_entry_loaning.id, 'res_model': 'account.move'})
    
        elif transaction_type == 'deposit':
             for x in self.second_wizard_data.company:
                header =  {
                    'move_type': 'entry',
                    'date': date,
                    'budget_date': date,
                    'ref': reference,
                    'line_ids': [],
                    'company_id': x.id,
                }
                company_lines = self.second_wizard_data.filtered_domain([('company', '=', x.id)])
                partner = self.env['res.company'].browse(company_disbursement)        
                credit = {
                    'account_id': company_lines.account_loan.id,
                    'partner_id': partner.partner_id.id,
                    'name': 'Loan',
                    'credit': 0.0,
                    'debit': round(sum(company_lines.mapped('amount')), 2),
                }
                lines = []
                lines.append(Command.create(credit))
                for y in company_lines:
                    loan_lines = {
                        'account_id': y.account.id,
                        'product_id': y.product.id,
                        'analytic_distribution': {str(y.analytic_account.id): 100.0},
                        'partner_id': supplier,
                        'name': y.label,
                        'billable': y.billable,
                        'markup': y.markup,
                        'credit': round(y.amount, 2),
                        'debit':0.0,
                    }
                    lines.append(Command.create(loan_lines))
                header['line_ids'] += lines
                journal_entry_loaning = self.env['account.move'].with_company(x).create(header)
                journal_entry_loaning.action_post()
                journal_entry_loaning.message_post(body=notes)
                attachment_loaning = self.env["ir.attachment"]
                for attachment_id in attachments:
                    attachment_loaning = attachment_loaning.browse(attachment_id)
                    attachment_loaning.copy({'res_id': journal_entry_loaning.id, 'res_model': 'account.move'})

            
    def confirm(self):
        attachments = self._context.get('default_attachment_ids')
        loan_amount = self._context.get('default_loan_amount')
        notes = self._context.get('default_notes')

        lines = []
        errors = []
        total = 0
        for x in self.second_wizard_data:
                total = x.amount + total
                total = round(total, 2)       

        for x in self.second_wizard_data:
            missing_fields = []
            if not x.company:
                missing_fields.append('Company')
            if not x.account:
                missing_fields.append('Account')
            if not x.account_loan:
                missing_fields.append('Loan Account')
            if x.amount <= 0:
                missing_fields.append('Amount')
            if missing_fields:
                errors.append('Please fill the following fields: ' + ', '.join(missing_fields))
            if errors:
                error_message = '\n'.join(errors)
                raise ValidationError(error_message)
            elif total != loan_amount:
                raise ValidationError('The move is not balanced. The total loan amount is $' + str(loan_amount) + ' and the total amount of the lines is $' + str(total) + '.')
            else:
                line = self._create_line_company_disbursement(x)
                lines.append(Command.create(line))
            
        header = self._create_header_company_disbursement()
        header['line_ids'] += lines 

        journal_entry = self.env["account.move"].sudo().create(header)
        journal_entry.action_post()
        journal_entry.message_post(body=notes)

        attachment = self.env["ir.attachment"]
        for attachment_id in attachments:
            attachment = attachment.browse(attachment_id)
            attachment.copy({'res_id': journal_entry.id, 'res_model': 'account.move'})

        if self.second_wizard_data:
            self._create_header_company_loaning()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': journal_entry.id,
            'target': 'current',  
        }

        return action

    def go_back(self):
        company_disbursement = self._context.get('default_company_disbursement')
        supplier = self._context.get('default_supplier')
        loan_amount = self._context.get('default_loan_amount')
        loan_account = self._context.get('default_loan_account')
        account_bank = self._context.get('default_account_bank')
        date = self._context.get('default_date')
        reference = self._context.get('default_reference')
        attachments = self._context.get('default_attachment_ids')
        transaction_type = self._context.get('default_transaction_type')

        first_wizard = self.env.ref('accounting_wizard.view_loan_between_companies_wizard_form')
        return {
            'name': 'Loans Between Companies Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'loans.between.companies',
            'view_mode': 'form',
            'views': [(first_wizard.id, 'form')],
            'view_id': first_wizard.id,
            'target': 'new',
            'context': {
                'default_company_disbursement': company_disbursement,
                'default_transaction_type': transaction_type,
                'default_supplier': supplier,
                'default_loan_amount': loan_amount,
                'default_loan_account': loan_account,
                'default_account_bank': account_bank,
                'default_date': date,
                'default_reference': reference,
                'default_attachment_ids': attachments,
            }
        }


