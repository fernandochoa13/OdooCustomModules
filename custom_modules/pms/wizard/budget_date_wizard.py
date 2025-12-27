from odoo import models, fields, api

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

class BudgetDateWizard(models.TransientModel):
    _name = 'budget.date.wizard'
    _description = 'Budget Date Wizard'

    date = fields.Date(string='Budget Date', required=True)

    def set_budget_date(self):
        res_ids = self.env.context.get('active_ids')
        records = self.env["account.move"].search([('id', '=', res_ids)])
        for record in records:
            record.sudo().write({'budget_date': self.date})
        return {'type': 'ir.actions.act_window_close'}



    
