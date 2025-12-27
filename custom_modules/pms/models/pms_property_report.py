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

class pms_property_report_pin_wizard(models.TransientModel):
    _name = 'pms.property.report.pin.wizard'
    _description = 'Property Report Verification Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)

    def verification_action(self):
        self.ensure_one()

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

        if pin_verification:
            tree_view = self.env.ref('pms.pms_property_report_tree')
            form_view = self.env.ref('pms.pms_property_report_form')
            return {
                'name': 'PMS Property Reports',
                'type': 'ir.actions.act_window',
                'res_model': 'pms.property.report',
                'view_mode': 'tree',
                'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
                'view_id': tree_view.id,
                'target': 'current',
            }
        else:
            raise ValidationError(_('Invalid Employee PIN'))

class PMSPropertyReport(models.Model):
    _name = "pms.property.report"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "PMS Property Report"

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    property_name = fields.Many2one('pms.property', string='Property', readonly=True)
    county = fields.Many2one(related="property_name.county", string='County', readonly=True)
    project_manager = fields.Many2one(related="property_name.projects.project_manager", string='Project Manager', readonly=True)
    superintendent = fields.Many2one(related="property_name.projects.superintendent", string='Superintendent', readonly=True)
    zone_coordinator = fields.Many2one(related="property_name.projects.zone_coordinator", string='Zone Coordinator', readonly=True)
    property_status = fields.Selection(related="property_name.utility_phase", string="Property Status", readonly=True)
    report_date = fields.Date(string='Date', default=fields.Date.today(), readonly=True)
    inspections_in_progress = fields.Many2many('pms.inspections.type', string='Inspections In Progress', readonly=True)                                       
    inspections_to_request = fields.One2many('property.inspections.type.lines', 'property_record_id', string='Inspections To Request', readonly=True)
    materials_notes = fields.Text(string='Materials Notes', readonly=True)
    contractors_in_progress = fields.One2many('property.contractors', 'property_record_id', string='Contractors In Progress', readonly=True)
    expected_co_date = fields.Date(string='Expected CO Date', readonly=True)
    attachments = fields.Many2many('ir.attachment', 'pms_property_report_attachment_rel', 'property_report_id', 'attachment_id', string='Attachments', readonly=True)

class PMSInspectionsTypeLines(models.Model):
    _name = "property.inspections.type.lines"
    _description = "Table for Inspections Type"

    inspections = fields.Many2one('pms.inspections.type', string='Inspection Type')
    property_report_date = fields.Date(string='Date')
    property_record_id = fields.Many2one('pms.property.report', string='Property Record ID')

class PMSContractorsInProgress(models.Model):
    _name = "property.contractors"
    _description = "Table for Contractors"

    property_record_id = fields.Many2one('pms.property.report', string='Property Record ID')
    contractors = fields.Many2one('res.partner', string='Contractor')
    job_status = fields.Selection([('to_execute', 'To Execute'), ('in_execution', 'In Execution'), ('finished', 'Finished'),], string='Job Status')