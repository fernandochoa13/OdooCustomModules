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


class DailyReport(models.Model):
    _name = "daily.report"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Daily Report"

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True, required=True)
    employee_name = fields.Char(string='Employee Name', required=True)  
    date = fields.Date(string='Date', required=True, default=fields.Date.today(), readonly=True)
    general_summary = fields.Text(string='General Summary', required=True, readonly=True)
    wins = fields.Text(string='Wins of the Day', readonly=True)
    losses = fields.Text(string='Losses of the Day', readonly=True)
    urgent_needs = fields.Text(string='Urgent Needs', readonly=True)
    questions = fields.Text(string='Questions', readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    missed_days = fields.Char(string='Missed Report On', store=True)

    @api.depends('employee_name', 'date')
    def _compute_name(self):
        for record in self:
            record.name = f'{record.employee_name} - {record.date}'

    def _compute_missed_days(self):
        hr_employee = self.env['hr.employee'].search([])
        today = fields.Date.today()
        for employee in hr_employee:
                reports = self.env['daily.report'].search(['&', ('employee_id', '=', employee.id), ('date', '=', today)])
                if not reports:
                    missed_record = {
                        'employee_id': employee.id,
                        'employee_name': employee.name,
                        'date': today,
                        'general_summary': 'No Report Submitted',
                        'missed_days': f'{fields.Date.today()}',
                    }
                    self.env['daily.report'].create(missed_record)

class DailyReportWizard(models.TransientModel):
    _name = "daily.report.wizard"
    _description = "Daily Report Wizard"

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.user.employee_id.id, required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    general_summary = fields.Text(string='General Summary', required=True)
    wins = fields.Text(string='Wins of the Day')
    losses = fields.Text(string='Losses of the Day')
    urgent_needs = fields.Text(string='Urgent Needs')
    questions = fields.Text(string='Questions')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model
    def action_refresh_page(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_create_report(self):
        self.ensure_one()

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

        if pin_verification:

            report = self.env['daily.report'].create({
                'employee_id': self.employee_id.id,
                'employee_name': self.employee_id.name,
                'date': self.date,
                'general_summary': self.general_summary,
                'wins': self.wins,
                'losses': self.losses,
                'urgent_needs': self.urgent_needs,
                'questions': self.questions
            })

            attachment_ids = self.attachment_ids.ids
            attachment = self.env["ir.attachment"]
            for attachment_id in attachment_ids:
                attachment = attachment.browse(attachment_id)
                attachment.copy({'res_id': report.id, 'res_model': 'daily.report'})

            # Reload Page
            return {
                'type': 'ir.actions.act_url',
                'url': '/web',
                'target': 'self',
                # 'next': {
                #     'type': 'ir.actions.client', 
                #     'tag': 'display_notification',
                #     'params': {
                #         'message': "Report successfully created.", 
                #         'type': 'info', 
                #         'sticky': False
                #     }
                # }
            }
            
            
        else:
            raise ValidationError(_('Invalid Employee PIN'))
        
class ManagerReportWizard(models.TransientModel):
    _name = "manager.report.wizard"
    _description = "Manager Report Wizard"

    manager_id = fields.Many2one('hr.employee', string='Manager', default=lambda self: self.env.user.employee_id.id, required=True)
    manager_pin = fields.Char(string='Manager PIN', required=True)

    def action_view_reports(self):
        self.ensure_one()

        pin_verification = self.env['hr.employee'].search([('id', '=', self.manager_id.id), ('pin', '=', self.manager_pin)])

        if pin_verification:
            tree_view = self.env.ref('accounting_wizard.daily_report_tree')
            form_view = self.env.ref('accounting_wizard.daily_report_form')
            return {
                'name': 'Manager Daily Reports',
                'type': 'ir.actions.act_window',
                'res_model': 'daily.report',
                'view_mode': 'tree,form',
                'domain': ['|', ('employee_id.parent_id', '=', self.manager_id.id), ('employee_id.report_manager', 'in', self.manager_id.id)],
                'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
                'view_id': tree_view.id,
                'target': 'current',
            }
        else:
            raise ValidationError(_('Invalid Manager PIN'))



class MissingReportsWizard(models.TransientModel):
    _name = "missing.reports.wizard"
    _description = "Missing Reports Wizard"

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def generate_missing_reports(self):
        self.ensure_one()
        context = {
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'missing.reports.tree',
            'view_mode': 'tree',
            'res_model': 'missing.reports',
            'context': context,
        }
    
class MissingReportPinWizard(models.TransientModel):
    _name = "missing.report.pin.wizard"
    _description = "Missing Report PIN Wizard"

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.user.employee_id.id, required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)

    def confirm_user(self):
        self.ensure_one()

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

        if pin_verification:
            missing_wizard = self.env.ref('accounting_wizard.missing_report_wizard_form')
         
            return {
                'name': 'Missing Reports Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'missing.reports.wizard',
                'views': [(missing_wizard.id, 'form')],
                'view_id': missing_wizard.id,
                'target': 'new',
            }

        else:
            raise ValidationError(_('Invalid Employee PIN'))

class MyReportWizard(models.TransientModel):
    _name = "my.report.wizard"
    _description = "My Reports Wizard"

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.user.employee_id.id, required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)

    def confirm_user(self):
        self.ensure_one()

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

        if pin_verification:
            tree_view = self.env.ref('accounting_wizard.daily_report_tree')
            form_view = self.env.ref('accounting_wizard.daily_report_form')
            return {
            'name': 'My Daily Reports',
            'type': 'ir.actions.act_window',
            'res_model': 'daily.report',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'view_id': tree_view.id,
            'target': 'current',
        }

        else:
            raise ValidationError(_('Invalid Employee PIN'))
    
class HrEmployeeInherit(models.Model):
    _inherit = "hr.employee"

    def is_checked_in(self):
        self.ensure_one()
        return self.sudo().last_attendance_id.check_out is None
