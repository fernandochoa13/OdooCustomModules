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

class MatOrderBillWizard(models.TransientModel):
    _name = 'material.order.bill.wizard'
    _description = 'Material Order Wizard'


    def continue_bill(self):
        property_id = self.env.context.get('default_property_id')
        invoice_origin = self.env.context.get('default_invoice_origin')
        material_lines = self.env.context.get('default_material_lines')
        property_owner = self.env.context.get('default_partner_id')
        order_id = self.env.context.get('default_order_id')
        status = self.env.context.get('order_status')

        property_order = self.env['pms.property'].browse(property_id) 
        order = self.env['pms.materials'].browse(order_id)
        mat_lines = self.env['pms.materials.lines'].browse(material_lines)

        if not order.create_a_bill:
            order.write({
                'order_status': 'ordered',
                'ordered_date': fields.Datetime.now()
            })
            return self.env['update.owner.call.day'].simple_notification("warning", False, 'Create bill is disabled, skipping bill logic from Material Order Bill Wizard.', False)
        elif order.has_bill == True:
            raise UserError(_('Bill already created for this order.'))
        else:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': property_owner,
                'invoice_date': fields.Date.today(),
                'invoice_origin': invoice_origin,
                'invoice_line_ids': [(0, 0, {
                    'name': line.product.name,
                    'product_id': line.product.id,
                    'analytic_distribution': {str(property_order.analytical_account.id): 100.0},
                    'quantity': line.quantity,
                    'price_unit': line.amount,
                }) for line in mat_lines],
            })
            bill.action_post()
            var = {
                'linked_bill': bill.id,
                'has_bill': True,
                'order_status': 'ordered',
                'ordered_date': fields.Datetime.now()
            }
            order.write(var)
            # order.linked_bill = bill.id
            # order.has_bill = True
            # order.order_status = 'ordered'
            # order.ordered_date = fields.Datetime.now() # added
            if status == 'gave_payment':
                if order.paid_with_other_company == False:
                    order.create_payment()
                    domain = [
                        ('parent_state', '=', 'posted'),
                        ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                        ('reconciled', '=', False),
                    ]
                    bill = self.env['account.move'].browse(order.linked_bill.id)
                    payment = self.env['account.payment'].browse(order.linked_payment.id)
                    bill_line = bill.line_ids.filtered_domain(domain)
                    payment_line = payment.line_ids.filtered_domain(domain)
                    
                    for account in payment_line.account_id:
                        (payment_line + bill_line)\
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                            .reconcile()
                    # Redundant code
                    # order.order_status = 'ordered'
                    # order.ordered_date = fields.Datetime.now() # added
                    
                elif order.paid_with_other_company == True:
                    domain = [
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('reconciled', '=', False),
                    ]
                    bill = self.env['account.move'].browse(order.linked_bill.id)
                    payment = self.env['account.move'].browse(order.main_journal_entry.id)
                    bill_line = bill.line_ids.filtered_domain(domain)
                    payment_line = payment.line_ids.filtered_domain(domain)
                    
                    for account in payment_line.account_id:
                        (payment_line + bill_line)\
                            .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                            .reconcile()
                    # Redundant code
                    # order.order_status = 'ordered'
                    # order.ordered_date = fields.Datetime.now() # added
                    
            order.create_request_payment(company=self.env.company.id)
            message = 'Order %s on property %s has been ordered.' % (order.name, order.property_id.name)
            order._send_sms_messages(message)
            return {
                'type': 'ir.actions.act_window',
                'name': ('account.view_move_form'),
                'res_model': 'account.move',
                'res_id': bill.id,
                'view_mode': 'form'
            }