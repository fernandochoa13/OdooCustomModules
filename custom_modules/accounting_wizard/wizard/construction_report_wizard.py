
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


class ConstructionReportWizard(models.TransientModel):
    _name = "construction.report.wizard"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Construction Report Wizard"

    property_id = fields.Many2one('pms.property', string='Property', required=True)
    escrow_property = fields.Boolean(string='Escrow Property', compute="_compute_escrow_property", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)

    @api.depends('property_id')
    def _compute_escrow_property(self):
        check_escrow = self.env['pms.projects'].search([('address', '=', self.property_id.id)])

        if check_escrow.custodial_money == True:
            self.escrow_property = True
        else:
            self.escrow_property = False 

    def get_report(self):
        if self.property_id:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'construction.report.tree',
                    'res_model': 'construction.report',
                    'view_mode': 'tree',
                    'context': {'default_property_id': self.property_id.id,
                                'default_escrow_property': self.escrow_property,
                                'default_company': self.company_id.id},
                }

class ConstructionReport(models.Model):
    _name = 'construction.report'
    _description = "Construction Report"
    _auto = False 

    id = fields.Integer(readonly=True)
    property_name = fields.Char(readonly=True)
    owner_name = fields.Char(readonly=True)
    house_model = fields.Char(readonly=True)
    code = fields.Char(readonly=True)
    # company = fields.Char(readonly=True)
    product = fields.Char(readonly=True)
    real_cost = fields.Float(readonly=True)
    budget_amount = fields.Float(readonly=True)
    difference = fields.Float(readonly=True)
    proyected_cost = fields.Float(readonly=True)
    #county = fields.Char(readonly=True)
    city = fields.Char(readonly=True)

    def view_product_detail(self):
        property_id = self.env.context.get('default_property_id')
        escrow_property = self.env.context.get('default_escrow_property')
        company_id = self.env.context.get('default_company')

        property_record = self.env['pms.property'].browse(property_id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Product Detail',
            'res_model': 'account.analytic.line',
            'view_mode': 'tree',
            'domain': [('product_id.name', '=', self.product),('account_id', '=', property_record.analytical_account.id), ('company_id', '=', company_id), ('general_account_id.code', '=', '1000201')],
        }

    @property
    def _table_query(self):
        property_id = self.env.context.get('default_property_id')
        # escrow_property = self.env.context.get('default_escrow_property')
        company_id = self.env.context.get('default_company')

        return f"""
SELECT 
ROW_NUMBER() OVER() as id,
pms_property.name as property_name,
pms_property.city as city, 
res_partner.name as owner_name, 
pms_housemodels.name as house_model,
product_template.default_code as code,
product_template.name ->> 'en_US' as product, 
COALESCE(SUM(analytic_lines.amount), 0) as real_cost, 
            
COALESCE(MAX(budget.amount), 0) as budget_amount,

COALESCE(MAX(budget.amount), 0) + COALESCE(SUM(analytic_lines.amount), 0) as difference,
GREATEST(ABS(COALESCE(SUM(analytic_lines.amount), 0)), ABS(COALESCE(MAX(budget.amount), 0))) as proyected_cost 

FROM pms_property
LEFT JOIN pms_housemodels ON pms_property.house_model = pms_housemodels.id
LEFT JOIN res_partner ON pms_property.partner_id = res_partner.id

LEFT JOIN (
SELECT budget_model.house_model as house_model, budget_model.city as city, budget_model.product_model as product_model, SUM(budget_model.amount) as amount
FROM budget_model
GROUP BY budget_model.house_model, budget_model.city, budget_model.product_model
) budget
ON pms_housemodels.id = budget.house_model
AND pms_property.city = budget.city

LEFT JOIN product_template ON budget.product_model = product_template.id
LEFT JOIN product_product ON product_template.id = product_product.product_tmpl_id
LEFT JOIN (
SELECT account_analytic_line.account_id as account_id, account_analytic_line.company_id as company_id, account_analytic_line.general_account_id as general_account_id, account_analytic_line.product_id as product_id, SUM(account_analytic_line.amount) as amount
FROM account_analytic_line
GROUP BY account_analytic_line.account_id, account_analytic_line.company_id, account_analytic_line.general_account_id, account_analytic_line.product_id
) analytic_lines

ON product_product.id = analytic_lines.product_id
AND pms_property.analytical_account = analytic_lines.account_id
AND analytic_lines.company_id = {company_id}
AND (
analytic_lines.general_account_id IN (SELECT id FROM account_account WHERE code = '1000201') 
OR analytic_lines.general_account_id IS NULL
)


WHERE pms_property.id = {property_id}

GROUP BY pms_property.name, res_partner.name, pms_housemodels.name, product_template.default_code, product_template.name, pms_property.city

        """

#WHERE account_account.name ILIKE '%escrow%' AND account_analytic_line.product_id IS NOT NULL AND pms_property.id = {property_id} AND account_analytic_line.company_id = {company_id}
                    