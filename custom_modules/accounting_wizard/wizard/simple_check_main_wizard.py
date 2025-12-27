
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


class SimpleCheckMainWizard(models.TransientModel):
    _name = "simple.check.main.wizard"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Simple Check Main Wizard"

    vendor = fields.Many2one('res.partner', string='Vendor', required=True)
    date = fields.Date(string='Date', required=True)
    company = fields.Many2one('res.company', string='Company', required=True)
    bank = fields.Many2one('account.journal', string='Bank', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', required=True)
    
    def next(self):
        second_wizard = self.env.ref('accounting_wizard.second_wizard_form')
        attachments_ids = self.attachment_ids.ids

        return {
           'name': 'Simple Check Wizard',
           'type': 'ir.actions.act_window',
           'view_mode': 'form',
           'res_model': 'second.wizard',
           'views': [(second_wizard.id, 'form')],
           'view_id': second_wizard.id,
           'target': 'new',
            'context': {
                 'default_vendor': self.vendor.id,
                 'default_date': self.date,
                 'default_company': self.company.id,
                 'default_bank': self.bank.id,
                 'default_attachment_ids': attachments_ids,
             }
       }

class SecondWizard(models.TransientModel):
    _name = "second.wizard"
    _description = "Simple Check Wizard"

    property_account = fields.Many2one('account.analytic.account', string='Property Account')
    company_context = fields.Many2one('res.company', string='Company', compute='_compute_company')
    product = fields.Many2one('product.product', string='Product')
    account = fields.Many2one("account.account", string='Account')
    amount = fields.Monetary(string='Amount', currency_field='company_currency_id')
    split_tree = fields.Many2one('split.wizard', string='Split')

    company_id = fields.Many2one(
         comodel_name='res.company',
         string='Accounting Company',
         default=lambda self: self.env.company
     )

    company_currency_id = fields.Many2one(
         string='Company Currency',
         related='company_id.currency_id', readonly=True
     )
    
    def _compute_company(self):
        self.company_context = self._context.get('default_company')

    def go_back(self):
        vendor_gb = self._context.get('default_vendor')
        date_gb = self._context.get('default_date')
        company_gb = self._context.get('default_company')
        attachments = self._context.get('default_attachment_ids')
        bank = self._context.get('default_bank')

        first_wizard = self.env.ref('accounting_wizard.view_simple_check_main_wizard_form')
        return {
            'name': 'Simple Check Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'simple.check.main.wizard',
            'view_mode': 'form',
            'views': [(first_wizard.id, 'form')],
            'view_id': first_wizard.id,
            'target': 'new',
            'context': {
                'default_vendor': vendor_gb,
                'default_date': date_gb,
                'default_company': company_gb,
                'default_bank': bank,
                'default_attachment_ids': attachments,
            }
        }
    
    def split(self):
        vendor = self._context.get('default_vendor')
        date = self._context.get('default_date')
        company = self._context.get('default_company')
        bank = self._context.get('default_bank') 
        attachments = self._context.get('default_attachment_ids') 

        split_wizard = self.env.ref('accounting_wizard.view_split_wizard_form')
        return {
            'name': 'Split Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'split.wizard',
            'view_mode': 'form',
            'views': [(split_wizard.id, 'form')],
            'view_id': split_wizard.id,
            'target': 'new',
            'context': {
                'default_vendor': vendor,
                'default_date': date,
                'default_company': company,
                'default_bank': bank,
                'default_attachment_ids': attachments
            }
        }
        
    @api.onchange('product')
    def onchange_product_id(self):
        if self.product:
            self.account = self.product.categ_id.property_account_expense_categ_id
            
    def _second_wizard_header(self):
        vendor_c = self._context.get('default_vendor')
        date_c = self._context.get('default_date')
        company_c = self._context.get('default_company')

        header = {
            'move_type': 'in_invoice',
            'date': date_c,
            'invoice_date': date_c,
            'invoice_line_ids': [],
            'partner_id': vendor_c,
            'company_id': company_c,
        }
        return header

    def _second_wizard_line(self, x=None):
        line = {
            'product_id': self.product.id,
            'account_id': self.account.id,
            "quantity": 1,
            'price_unit': self.amount,
        }
        if x and x.get("account"):
            line["analytic_distribution"] = {str(x["account"]): 100.0}
        return line

    def confirm(self):
        vendor_c = self._context.get('default_vendor')
        date_c = self._context.get('default_date')
        bank = self._context.get('default_bank')
        attachments = self._context.get('default_attachment_ids')

        header = self._second_wizard_header()
        lines = []

        if self.property_account:
            for x in self.property_account:
                lines.append(Command.create(self._second_wizard_line({"account": x.id})))
        else:
            lines.append(Command.create(self._second_wizard_line()))

        header['invoice_line_ids'] += lines

        bill = self.env["account.move"].sudo().create(header)
        bill.action_post()

        attachment = self.env["ir.attachment"]
        for attachment_id in attachments:
            attachment = attachment.browse(attachment_id)
            attachment.copy({'res_id': bill.id, 'res_model': 'account.move'})

        bank_id = self.env['account.journal'].browse(bank)
        check = {
            'partner_id': vendor_c,
            'amount': self.amount,
            'date':date_c,
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'journal_id': bank_id.id,
            'payment_method_line_id': bank_id.outbound_payment_method_line_ids.filtered_domain([('name', '=', 'Checks')]).id,
        }

        new_check = self.env['account.payment'].create(check)
        new_check.action_post()

        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('reconciled', '=', False),
        ]

        bill_line = bill.line_ids.filtered_domain(domain)
        payment_line = new_check.line_ids.filtered_domain(domain)

        for account in payment_line.account_id:
            (payment_line + bill_line)\
                .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                .reconcile()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': new_check.id,
            'target': 'current',
        }
        return action

class SplitWizard(models.TransientModel):
    _name = "split.wizard"
    _description = "Split Wizard"

    second_wizard_data = fields.One2many('second.wizard', 'split_tree')

    def _split_wizard_header(self):
        vendor_c = self._context.get('default_vendor')
        date_c = self._context.get('default_date')
        company_c = self._context.get('default_company')

        header = {
                'move_type': 'in_invoice',
                'date': date_c,
                'invoice_date': date_c,
                'invoice_line_ids': [],
                'partner_id': vendor_c,
                'company_id': company_c,
            }
        return header
    
    def _split_wizard_line_multiple(self, x=None):
        lines = {
            'product_id': x.product.id,
            'account_id': x.account.id,
            'quantity': 1,
            'price_unit': x.amount,
        }
        if x.property_account:
            lines["analytic_distribution"] = {str(x.property_account.id): 100.0}
        return lines

    def confirm(self):
        vendor_split = self._context.get('default_vendor')
        date_split = self._context.get('default_date')
        attachments = self._context.get('default_attachment_ids')
        company = self._context.get('default_company')
        bank = self._context.get('default_bank')
        total_amount = sum(self.second_wizard_data.mapped('amount'))

        print(company)

        lines = []
        for x in self.second_wizard_data:
            line = self._split_wizard_line_multiple(x)
            lines.append(Command.create(line))
            
        header = self._split_wizard_header()
        header['invoice_line_ids'] += lines 

        bill = self.env["account.move"].sudo().create(header)
        bill.action_post()

        attachment = self.env["ir.attachment"]
        for attachment_id in attachments:
            attachment = attachment.browse(attachment_id)
            attachment.copy({'res_id': bill.id, 'res_model': 'account.move'})

        bank_id = self.env['account.journal'].browse(bank)
        check ={
            'partner_id': vendor_split,
            'amount':total_amount,
            'date': date_split,
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'journal_id': bank_id.id,
            'payment_method_line_id': bank_id.outbound_payment_method_line_ids.filtered_domain([('name', '=', 'Checks')]).id,
        }

        new_check = self.env['account.payment'].create(check)
        new_check.action_post()

        domain = [
            ('parent_state', '=', 'posted'),
            ('account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('reconciled', '=', False),
        ]
        
        bill_line = bill.line_ids.filtered_domain(domain)
        payment_line = new_check.line_ids.filtered_domain(domain)
        
        for account in payment_line.account_id:
             (payment_line + bill_line)\
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                    .reconcile()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': new_check.id,
            'target': 'current',  
        }

        return action


    def go_back(self):
        vendor_gb = self._context.get('default_vendor')
        date_gb = self._context.get('default_date')
        company_gb = self._context.get('default_company')
        property_account_split = self._context.get('default_property_account')
        amount_second = self._context.get('default_amount')
        product_split = self._context.get('default_product')
        account_split = self._context.get('default_account')
        bank = self._context.get('default_bank')
        attachments = self._context.get('default_attachment_ids')


        second_wizard = self.env.ref('accounting_wizard.second_wizard_form')
        return {
            'name': 'Simple Check Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'second.wizard',
            'view_mode': 'form',
            'views': [(second_wizard.id, 'form')],
            'view_id': second_wizard.id,
            'target': 'new',
            'context': {
                'default_vendor': vendor_gb,
                'default_date': date_gb,
                'default_company': company_gb,
                'default_property_account': property_account_split,
                'default_product': product_split,
                'default_account': account_split,
                'default_bank': bank,
                'default_amount': amount_second,
                'default_attachment_ids': attachments,
            }
        }
    