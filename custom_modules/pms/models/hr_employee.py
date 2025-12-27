# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from pytz import UTC
from datetime import datetime, time
from random import choice
from string import digits
from werkzeug.urls import url_encode
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import format_date, Query

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    report_manager = fields.Many2many(
        'hr.employee',
        'employee_report_manager_rel',  # This is the relation table name
        'employee_id',                  # This is the current model field
        'report_manager_id',            # This is the related model field
        string='Report Managers'
    )

    access_to_modify_records = fields.Boolean(string="Access to Modify Records", default=False)
    company_id = fields.Many2one('res.company', required=False)
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        pass