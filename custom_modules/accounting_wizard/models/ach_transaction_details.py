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
from datetime import date, timedelta
from odoo import api, models, fields
from odoo.tools import SQL
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
from odoo.fields import Command
from datetime import date
import pandas as pd
import base64
import io
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict
from cryptography.fernet import Fernet
import os
from collections import defaultdict
import math
import re
import string


class ACHTransactionDetails(models.Model):
    _name = "ach.transaction.details"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "ACH Transaction Details"

    account_holder = fields.Char(string='Account Holder')
    account_number = fields.Char(string='Account Number')
    routing_number = fields.Char(string='Routing Number')
    date = fields.Date(string='Date', default=fields.Date.today(), readonly=True)
    reference_ach = fields.Char(string='Reference Transaction')
    signature_attachment = fields.Binary(string='Signature Attachment')
    signed_by = fields.Char(string='Signed By')

class AccountPayment(models.Model):
    _inherit = ["account.payment"]

    account_number = fields.Char(string="Account Number", compute="_compute_account_number", readonly=True)
    account_holder = fields.Char(string="Account Holder", compute="_compute_account_holder", readonly=True)
    routing_number = fields.Char(string="Routing Number", compute="_compute_routing_number", readonly=True)
    signed_by = fields.Char(string="Signed By", compute="_compute_signed_by", readonly=True)

    @api.depends('payment_transaction_id.reference')
    def _compute_account_number(self):
        for payment in self:
            if payment.payment_transaction_id:
                ach_transaction = self.env['ach.transaction.details'].search([
                    ('reference_ach', '=', payment.payment_transaction_id.reference)
                ], limit=1)
                if ach_transaction:
                    payment.account_number = ach_transaction.account_number
                else:
                    payment.account_number = False
            else:
                payment.account_number = False

    @api.depends('payment_transaction_id.reference')
    def _compute_account_holder(self):
        for payment in self:
            if payment.payment_transaction_id:
                ach_transaction = self.env['ach.transaction.details'].search([
                    ('reference_ach', '=', payment.payment_transaction_id.reference)
                ], limit=1)
                if ach_transaction:
                    payment.account_holder = ach_transaction.account_holder
                else:
                    payment.account_holder = False
            else:
                payment.account_holder = False

    @api.depends('payment_transaction_id.reference')
    def _compute_signed_by(self):
        for payment in self:
            if payment.payment_transaction_id:
                ach_transaction = self.env['ach.transaction.details'].search([
                    ('reference_ach', '=', payment.payment_transaction_id.reference)
                ], limit=1)
                if ach_transaction:
                    payment.signed_by = ach_transaction.signed_by
                else:
                    payment.signed_by = False
            else:
                payment.signed_by = False

    @api.depends('payment_transaction_id.reference')
    def _compute_routing_number(self):
        for payment in self:
            if payment.payment_transaction_id:
                ach_transaction = self.env['ach.transaction.details'].search([
                    ('reference_ach', '=', payment.payment_transaction_id.reference)
                ], limit=1)
                if ach_transaction:
                    payment.routing_number = ach_transaction.routing_number
                else:
                    payment.routing_number = False
            else:
                payment.routing_number = False
