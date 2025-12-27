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

class DailyLogsWizard(models.TransientModel):
    _name = 'daily.logs.wizard'
    _description = 'Daily Logs Wizard'

    property_name = fields.Many2one("pms.property", string="Property")
    message = fields.Text(string="Message")
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments', required=True)

    def send_daily_log(self):
        attachments = []
        for i in self.attachment_ids:
            attachments.append(i.id)
        self.property_name.message_post(body=self.message, attachment_ids=attachments)



    
