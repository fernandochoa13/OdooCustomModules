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

class InvoiceWizard(models.TransientModel):
    _name = 'invoice.wizard'
    _description = 'Invoice Wizard'

    company_id = fields.Many2one('res.company', string='Company')

    def create_invoice(self):
        res_ids = self.env.context.get('active_ids')
        print(res_ids)
        for record in res_ids:
            lines = []
            activity = self.env['pms.projects.routes'].search([('id', '=', record)])
            invoice = {
               'company_id': self.company_id.id,
               'partner_id': activity.project_property.address.partner_id.id,
               'move_type': 'out_invoice',
               'invoice_line_ids': [],
               'invoice_date': fields.Date.today(), 
               'state': 'draft',
            }

            invoice_line = {
                'product_id': activity.product.id,
                'quantity': 1,
                'analytic_distribution': {str(activity.project_property.address.analytical_account.id): 100.0},

            }
            activity.invoiced = True
            activity.invoice_counter += 1
            lines.append(Command.create(invoice_line))
            invoice['invoice_line_ids'] += lines
            created_invoice = self.env['account.move'].sudo().create(invoice)
            activity.invoice_id = created_invoice.id
            created_invoice.activity_id = activity.id

class AccountMove(models.Model):
    _inherit = 'account.move'

    activity_id = fields.Integer(string='Activity ID')

    def view_activity(self):
        if self.activity_id == False:
            raise UserError(_('No activity found'))
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('pms.pms_projects_routes_tree'),
                'res_model': 'pms.projects.routes',
                # 'res_id': self.activity_id,
                'domain': [('id', '=', self.activity_id)],
                'view_mode': 'tree',
            }


    
