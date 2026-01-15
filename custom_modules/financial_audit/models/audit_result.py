from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch
from odoo.tools.misc import clean_context, format_date

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


class AuditResult(models.Model):
    _name = "audit.result"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Audit Result"

    name = fields.Char(string='Name')
    test_name = fields.Many2one("audit.test", string='Test Name')
    company = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    memo = fields.Text(string='Memo')
    reason = fields.Text(string='Reason')
    solved = fields.Boolean(string='Solved')
    model = fields.Char(string='Model')
    record_id = fields.Char(string='Record ID')
    date = fields.Date(string=' Test Date')
    xml_view = fields.Char(string='XML View')

    def view_record(self):
        for record in self:
            action = {
                'type': 'ir.actions.act_window',
                "name": (record.xml_view),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': record.model,
                'res_id': int(record.record_id),
                #'domain': [("id", "=", record.record_id)],
                #"view_id": self.env.ref(record.xml_view).id,
                'target': 'new',
            }
            return action