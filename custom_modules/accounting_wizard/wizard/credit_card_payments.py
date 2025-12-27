
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


class CreditCardPayments(models.TransientModel):
    _name = "credit.card.payments"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Credit Card Payments"

    company = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    credit_card_journal = fields.Many2one('account.journal', string='Credit Card Journal', required=True)
    reference = fields.Char(string='Reference', required=True)
    bank = fields.Many2one('account.journal', string='Bank Journal', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='company_currency_id')

    company_currency_id = fields.Many2one(
         string='Company Currency',
         related='company.currency_id', readonly=True
     )
    
    def confirm(self):
        payment = {
            'move_type': 'entry',
            'invoice_date': self.date,
            'date': self.date,
            'budget_date': self.date,
            'ref': self.reference,
            'line_ids': [],
            'company_id': self.company.id,
        }

        lines = []
        line_debit = {
            'account_id': self.credit_card_journal.inbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
            'debit': self.amount,
            'credit': 0.0,
        }

        line_credit = {
            'account_id': self.bank.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
            'debit': 0.0,
            'credit': self.amount,
        }

        lines.append(Command.create(line_debit))
        lines.append(Command.create(line_credit))

        payment['line_ids'] += lines

        move = self.env['account.move'].create(payment)
        move.action_post()

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',  
        }

        return action