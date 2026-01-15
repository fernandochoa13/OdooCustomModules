from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch
from odoo.tools.misc import clean_context, format_date
from dateutil.relativedelta import relativedelta
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

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action

# from odoo.addons.account.models.account_move import MAX_HASH_VERSION

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

class AuditTest(models.Model):
    _name = "audit.test"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Audit Test"

    test_name = fields.Char(compute="_compute_name", string='Test Name', readonly=True, store=True)
    name = fields.Char(string='Name', required=True)
    test_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('annually', 'Annually'),
    ], string='Frequency', default='', store=True, required=True)
    search_record = fields.Text(string='Search Records')
    last_executed_on = fields.Date(string='Last Executed On', readonly=True)
    active = fields.Boolean(string='Active', default=True)
    next_date = fields.Date(string='Next Date', readonly=False)
    all_models = fields.Many2one("ir.model", string="Select Model")
    xml_view = fields.Many2one("ir.ui.view", string="Select View")
    memo = fields.Text(string='Memo')

    @api.depends("name","test_frequency")
    def _compute_name(self):
        for record in self:
            if record.name and record.test_frequency:
                record.test_name = f"{record.name} - {record.test_frequency}"
            else:
                record.test_name = " "

    @api.depends("search_record", "active", "test_frequency", "all_models")
    def run_test(self):
        today = fields.Date.today()
        if self.next_date == False and self.last_executed_on == False:
            self.last_executed_on = today
            self.next_date = today
        audits = self.search(["&",("active", "=", True), "|", ("next_date", "<=", today), ("next_date", "=", today)])
        if audits:
            for audit in audits:
                audit.last_executed_on = today
                audit._get_next_date()
                #for record in self:
                if audit.search_record:
                    result = self.env[audit.all_models.model].search([eval(audit.search_record)])
                    print(result)
                    if len(result.ids) > 0:
                        for res in result:
                            try:
                                if res.ref:
                                    audit.memo = res.ref
                            except:
                                try:
                                    if res.payment_reference:
                                        audit.memo = res.payment_reference
                                except:
                                    audit.memo = ""

                            results = {
                                "name": res.name,
                                "test_name": audit.id,
                                "company": res.env.company.id,
                                "memo": audit.memo,
                                "reason": "",
                                "solved": False,
                                "model": res._name,
                                "record_id": res.id,
                                "date": fields.Date.today(),
                                "xml_view": audit.xml_view.xml_id.split(".", 1)[1],
                            }
                            
                            res.env["audit.result"].create(results)
                        return results
                else:
                    raise UserError(_("You must define a search to run the test."))
                        
        else:
            raise UserError(_("An audit can't be run at this time or the test is not active."))
    
    def _get_next_date(self):
        # Get the next date based on the period and period count
        self.ensure_one()

        today = fields.Date.today()

        if self.test_frequency == "daily":
            self.next_date = today + timedelta(days=1)
            
        elif self.test_frequency == "weekly":
            self.next_date = today + timedelta(weeks=1)
            
        elif self.test_frequency == "monthly":
            self.next_date = today + relativedelta(months=1)

        elif self.test_frequency == "annually":
            self.next_date = today + relativedelta(years=1)
            
            


        
        

