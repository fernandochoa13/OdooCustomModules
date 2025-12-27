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

from collections import defaultdict
import math
import re
import string


class ReclassifyAccounts(models.Model):
    _name = "reclassify.accounts"
    _description = "Reclassify Accounts"

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)

    def open_journal_items(self):
        self.ensure_one()

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

        if pin_verification and pin_verification.access_to_modify_records == True:
            tree_view = self.env.ref('account.view_move_line_tree')
            return {
                'name': 'Journal Items',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move.line',
                'view_mode': 'tree',
                'domain': ['&', ('company_id', '=', self.env.company.id), ('parent_state', '=', 'posted')],
                'views': [(tree_view.id, 'tree')],
                'view_id': tree_view.id,
                'target': 'current',
            }
        else:
            raise ValidationError(_('Invalid Employee PIN or Employee does not have access to modify records.'))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def open_verify_wizard(self):

        return {
            'name': 'Verify Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'verify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
            },
        }
    
class VerifyWizard(models.Model):
        _name = "verify.wizard"
        _description = "Verify Wizard"

        employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
        employee_pin = fields.Char(string='Employee PIN', required=True)

        def open_accounts_wizard(self):
            selected_records = self.env.context.get('active_ids')

            pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

            if pin_verification and pin_verification.access_to_modify_records == True:
                return {
                    'name': 'Account Selector Wizard',
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.selector.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'active_ids': selected_records,
                                'company_id': self.env.company.id},
                }
            else:
                raise ValidationError(_('Invalid Employee PIN or Employee does not have access to modify records.'))
            
class AccountSelector(models.Model):
        _name = "account.selector.wizard"
        _description = "Account Selector Wizard"

        company_id = fields.Many2one('res.company', string='Company', default=lambda self: self._context.get('company_id'))

        account_to_change = fields.Many2one(
        'account.account', 
        string='Account to Change', 
        required=True,
        domain="[('company_id', '=', company_id)]"
        )

        def change_account(self):
            selected_records = self._context.get('active_ids')
            account_to_change = self.account_to_change

            for record in self.env['account.move.line'].browse(selected_records):
                record.account_id = account_to_change

            return {'type': 'ir.actions.act_window_close'}