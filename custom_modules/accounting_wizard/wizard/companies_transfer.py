
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


class companies_transfer(models.TransientModel):
    _name = "companies.transfer"
    _description = "Companies Transfers"

    from_company = fields.Many2one('res.company', string='From Company', required=True, default=lambda self: self.env.company)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    from_journal_id = fields.Many2one('account.journal', string='From Bank', required=True)
    reference = fields.Char(string='Reference', required=True)
    to_company = fields.Many2one('res.company', string='To Company', required=True, default=lambda self: self.env.company)
    bank = fields.Many2one('account.journal', string='To Bank/CC', required=True)
    amount = fields.Float(string='Amount', required=True)

    
    def confirm(self):
        payment = {
            'move_type': 'entry',
            'invoice_date': self.date,
            'date': self.date,
            'budget_date': self.date,
            'ref': self.reference,
            'line_ids': [],
            'company_id': self.from_company.id,
        }

        

        lines = []
        line_debit = {
            'account_id': self.from_journal_id.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
            'debit': 0.0,
            'credit': self.amount,
        }

        if self.from_company.id == self.to_company.id:
            line_credit = {
                'account_id': self.bank.inbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                'debit': self.amount,
                'credit': 0.0,
            }

            two_payment = False
        
        else:
            line_credit = {
                'account_id': self.env['account.account'].search(['&', ('company_id', '=', self.from_company.id), ('name', 'like', 'related')], limit=1).id,
                'debit': self.amount,
                'credit': 0.0,
                'partner_id': self.to_company.partner_id.id
            }


            two_payment = {
            'move_type': 'entry',
            'invoice_date': self.date,
            'date': self.date,
            'budget_date': self.date,
            'ref': self.reference,
            'line_ids': [],
            'company_id': self.to_company.id,
        }
            two_lines = []

            two_line_debit = {
            'account_id': self.bank.inbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
            'debit': self.amount,
            'credit': 0.0}

            two_line_credit = {
                'account_id': self.env['account.account'].search(['&', ('company_id', '=', self.to_company.id), ('name', 'like', 'related')], limit=1).id,
                'debit': 0.0,
                'credit': self.amount,
                'partner_id': self.from_company.partner_id.id
            }

            two_lines.append(Command.create(two_line_debit))
            two_lines.append(Command.create(two_line_credit))

            two_payment['line_ids'] += two_lines


            

        lines.append(Command.create(line_debit))
        lines.append(Command.create(line_credit))

        payment['line_ids'] += lines

        print(payment)
        print(two_payment)

        move = self.env['account.move'].sudo().create(payment)
        move.action_post()

        if two_payment:
            move_two = self.env['account.move'].sudo().create(two_payment)
            move_two.action_post()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',  
        }

        return action