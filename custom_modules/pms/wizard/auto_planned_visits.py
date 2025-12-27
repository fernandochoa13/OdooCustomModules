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
from datetime import datetime, timedelta
from collections import defaultdict
import math
import re
import string

from datetime import datetime, timedelta

class AutoPlannedVisitsWizard(models.TransientModel):
    _name = 'auto.planned.visits'
    _description = 'Automatic Planned Visits'

    def create_planned_visits(self):
        today = fields.Date.today()
        next_week_start = today if today.weekday() == 0 else today + timedelta(days=(7 - today.weekday()))

        projects = self.env['pms.projects'].search([
            '|',
            ('visit_day', '!=', False), 
            '|',
            ('second_visit_day', '!=', False),
            ('active', '!=', False)
        ])

        planned_visit_days = self.env['pms.planned.visit.days']

        for project in projects:
            visit_day = project.visit_day
            second_visit_day = project.second_visit_day

            visit_dates = []
            if isinstance(visit_day, str) and visit_day.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                visit_dates.append(self._next_weekday(today, visit_day))
            if isinstance(second_visit_day, str) and second_visit_day.lower() in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                visit_dates.append(self._next_weekday(today, second_visit_day))

            for visit_date in visit_dates:
                planned_visit_days.create({
                    'planned_property': project.address.id,
                    'planned_visit_date': visit_date,
                    'planned_visitor': project.superintendent.id,
                })

    def _next_weekday(self, start_date, weekday):
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        weekday_index = days.index(weekday.lower())
        start_weekday = start_date.weekday()
        days_ahead = (weekday_index - start_weekday + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        return start_date + timedelta(days=days_ahead)



