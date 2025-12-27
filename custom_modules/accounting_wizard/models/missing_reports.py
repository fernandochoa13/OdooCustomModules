
from odoo import api, fields, models, _, Command
from odoo import tools
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

class MissingReports(models.Model):
    _name = 'missing.reports'
    _description = "Missing Reports"
    _auto = False
    _order = 'id desc' 

    id = fields.Integer(readonly=True)
    employee_id = fields.Char(string="Employee ID")
    employee_name = fields.Char(string="Employee Name")
    date = fields.Date(string="Date")

    @property
    def _table_query(self):
        start_date = self.env.context.get('start_date')
        end_date = self.env.context.get('end_date')
        return f"""
            WITH date_series AS (
                SELECT generate_series(
                    '{start_date}'::date, 
                    LEAST('{end_date}'::date, CURRENT_DATE), 
                    '1 day'::interval
                ) AS date
            ),
            employee_dates AS (
                SELECT e.id as employee_id, e.name as employee_name, d.date
                FROM hr_employee e
                CROSS JOIN date_series d
            ),
            reported_dates AS (
                SELECT employee_id, date
                FROM daily_report
            ),
            combined_data AS (
                SELECT 
                    row_number() OVER () as id, 
                    ed.employee_id,
                    ed.employee_name,
                    ed.date
                FROM employee_dates ed
                LEFT JOIN reported_dates rd ON ed.employee_id = rd.employee_id AND ed.date = rd.date
                WHERE rd.date IS NULL
                AND ed.date BETWEEN '{start_date}' AND LEAST('{end_date}'::date, CURRENT_DATE)
            )
            SELECT * FROM combined_data
        """


