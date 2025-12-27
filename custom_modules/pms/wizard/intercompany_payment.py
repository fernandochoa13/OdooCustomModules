import base64
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta, datetime
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch
from odoo.tools.misc import clean_context, format_date
from odoo import http
from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference
import ast
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache
import requests
import json
#from intuitlib.exceptions import AuthClientError
import io
import zipfile
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action
from werkzeug import urls

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
import base64
import collections
import datetime
import hashlib
import pytz
import threading
import re

import requests
from collections import defaultdict
from random import randint
from werkzeug import urls

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class IntercompanyWizardCC(models.TransientModel):
    _name = "intercompany.wizard"
    _description = "Intercompany Wizard"

    company_to_pay = fields.Many2one('res.company', string='Company to Pay', required=True)
    card_journal = fields.Many2one('account.journal', string='Payment Journal', required=True, domain="[('company_id', '=', company_to_pay), ('type', 'in', ['cash', 'bank'])]")

    def make_intercompany_payment(self):
        main_company = self._context.get('default_company_id')
        amount = self._context.get('default_amount_total')
        provider = self._context.get('default_provider')
        record_id = self._context.get('default_id')
        reference = self._context.get('references')

        main_journal_entry_lines = [
            (0, 0, {
                'name': 'Loan between related companies',
                'partner_id': self.company_to_pay.partner_id.id,
                'account_id': self.env['account.account'].search([('code', '=', '200401'), ('company_id', '=', main_company)], limit=1).id,
                'debit': amount,
                'credit': 0.0,
            }),
            (0, 0, {
                'name': 'Account Payable',
                'account_id': self.env['account.account'].search([('code', '=', '211000'), ('company_id', '=', main_company)], limit=1).id,
                'credit': amount,
                'debit': 0.0,
            }),
        ]

        main_journal_entry = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'partner_id': provider,
            'company_id': main_company,
            'ref': reference,
            'date': fields.Date.today(),
            'line_ids': main_journal_entry_lines,
        })

        other_journal_entry_lines = [
            (0, 0, {
                'name': 'Loan between related companies',
                'partner_id': self.env['res.company'].search([('id', '=', main_company)]).partner_id.id,
                'account_id': self.env['account.account'].search([('code', '=', '200401'), ('company_id', '=', self.company_to_pay.id)], limit=1).id,
                'debit': 0.0,
                'credit':  amount,
            }),
            (0, 0, {
                'name': 'Outstanding Payments',
                'partner_id': provider,
                'account_id': self.card_journal.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                'debit': amount,
                'credit': 0.0,
            }),
        ]

        other_journal_entry = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'partner_id': provider,
            'ref': reference,
            'company_id': self.company_to_pay.id,
            'date': fields.Date.today(),
            'line_ids': other_journal_entry_lines,
        })

        main_journal_entry.action_post()
        other_journal_entry.action_post()

        domain = [
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('reconciled', '=', False),
                ]
        bill = self.env['account.move'].browse(record_id)
        payment = self.env['account.move'].browse(main_journal_entry.id)
        bill_line = bill.line_ids.filtered_domain(domain)
        payment_line = payment.line_ids.filtered_domain(domain)
        
        for account in payment_line.account_id:
            (payment_line + bill_line)\
                .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                .reconcile()
