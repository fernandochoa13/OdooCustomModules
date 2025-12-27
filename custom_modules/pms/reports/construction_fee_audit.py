import base64
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch
from odoo.tools.misc import clean_context, format_date
from odoo import http
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
import io
import zipfile
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action
from werkzeug import urls

#-*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict
import math
import re
import base64
import collections
import datetime
import hashlib
import pytz
import threading
import re

import requests
from collections import defaultdict
from random import randint
from werkzeug import urls

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class ConstructionFeeAudit(models.Model):
    _name = "construction.fee.audit"
    _description = "Construction Fee Audit"
    _auto = False

    id = fields.Integer(readonly=True)
    property_address = fields.Char(string='Property Address', readonly=True)
    county = fields.Char(string='County', readonly=True) 
    project_manager = fields.Char(string='Project Manager', readonly=True)
    zone_coordinator = fields.Char(string='Zone Coordinator', readonly=True) 
    superintendent = fields.Char(string='Superintendent', readonly=True) 
    house_model = fields.Char(string='House Model', readonly=True) 
    construction_status = fields.Char(string='Construction Status', readonly=True) 
    on_hold = fields.Boolean(string='On Hold', readonly=True) 
    parcel_id = fields.Char(string='Parcel ID', readonly=True) 
    custodial_money = fields.Boolean(string='Custodial Money', readonly=True) 
    own_third = fields.Char(string='Own/Third Party', readonly=True) 
    property_owner = fields.Char(string='Property Owner', readonly=True)
    const_fee_1st_created_date =  fields.Date(string='1st Construction Fee Creation Date', readonly=True)
    const_fee_1st_invoiced_date = fields.Date(string='1st Construction Fee Invoiced Date', readonly=True)
    const_fee_1st_paid_date = fields.Date(string='1st Construction Fee Paid Date', readonly=True)
    const_fee_2nd_created_date =  fields.Date(string='2nd Construction Fee Creation Date', readonly=True)
    const_fee_2nd_invoiced_date = fields.Date(string='2nd Construction Fee Invoiced Date', readonly=True)
    const_fee_2nd_paid_date = fields.Date(string='2nd Construction Fee Paid Date', readonly=True)
    const_fee_3rd_created_date =  fields.Date(string='3rd Construction Fee Creation Date', readonly=True)
    const_fee_3rd_invoiced_date = fields.Date(string='3rd Construction Fee Invoiced Date', readonly=True)
    const_fee_3rd_paid_date = fields.Date(string='3rd Construction Fee Paid Date', readonly=True)
    const_fee_final_created_date =  fields.Date(string='Final Construction Fee Creation Date', readonly=True)
    const_fee_final_invoiced_date = fields.Date(string='Final Construction Fee Invoiced Date', readonly=True)
    const_fee_final_paid_date = fields.Date(string='Final Construction Fee Paid Date', readonly=True)


    @property
    def _table_query(self):
        return f"""
        SELECT
    p.id AS id,
    pp.name AS property_address,
    pc.name AS county,
    he_pm.name AS project_manager,
    he_zc.name AS zone_coordinator,
    he_su.name AS superintendent,
    hm.name AS house_model,
    pp.on_hold AS on_hold,
    pp.parcel_id AS parcel_id,
    p.status_construction AS construction_status,
    p.custodial_money AS custodial_money,
    p.own_third_property AS own_third,
    rp.name AS property_owner,

    (SELECT MIN(pr.create_date)
     FROM pms_projects_routes pr
     JOIN pms_projects_routes_templates_lines prtl ON pr.name = prtl.id
     WHERE pr.project_property = p.id AND prtl.name ~* '1st Construction Fee') AS const_fee_1st_created_date,

    (SELECT MIN(pr.create_date)
     FROM pms_projects_routes pr
     JOIN pms_projects_routes_templates_lines prtl ON pr.name = prtl.id
     WHERE pr.project_property = p.id AND prtl.name ~* '2nd Construction Fee') AS const_fee_2nd_created_date,

    (SELECT MIN(pr.create_date)
     FROM pms_projects_routes pr
     JOIN pms_projects_routes_templates_lines prtl ON pr.name = prtl.id
     WHERE pr.project_property = p.id AND prtl.name ~* '3rd Construction Fee') AS const_fee_3rd_created_date,

    (SELECT MIN(pr.create_date)
     FROM pms_projects_routes pr
     JOIN pms_projects_routes_templates_lines prtl ON pr.name = prtl.id
     WHERE pr.project_property = p.id AND prtl.name ~* 'Final Construction Fee') AS const_fee_final_created_date,

    (SELECT MIN(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.move_id
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* '1st Construction Fee'
     ) AS subquery
     JOIN account_move am ON subquery.move_id = am.id AND am.state = 'posted'
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_1st_invoiced_date,

    (SELECT MIN(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.move_id
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* '2nd Construction Fee'
     ) AS subquery
     JOIN account_move am ON subquery.move_id = am.id AND am.state = 'posted'
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_2nd_invoiced_date,

    (SELECT MIN(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.move_id
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* '3rd Construction Fee'
     ) AS subquery
     JOIN account_move am ON subquery.move_id = am.id AND am.state = 'posted'
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_3rd_invoiced_date,

    (SELECT MIN(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.move_id
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* 'Final Construction Fee'
     ) AS subquery
     JOIN account_move am ON subquery.move_id = am.id AND am.state = 'posted'
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_final_invoiced_date,
	(SELECT MAX(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.matching_number
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* '1st Construction Fee' AND aml.matching_number IS NOT NULL
     ) AS subquery
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_1st_paid_date,

    (SELECT MAX(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.matching_number
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* '2nd Construction Fee' AND aml.matching_number IS NOT NULL
     ) AS subquery
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_2nd_paid_date,

    (SELECT MAX(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.matching_number
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* '3rd Construction Fee' AND aml.matching_number IS NOT NULL
     ) AS subquery
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_3rd_paid_date,

    (SELECT MAX(subquery.create_date)
     FROM (
         SELECT aml.create_date, aml.product_id, dist.key::integer AS analytic_account_id, aml.matching_number
         FROM account_move_line aml
         CROSS JOIN LATERAL jsonb_each_text(aml.analytic_distribution) AS dist(key, value)
         WHERE aml.name ~* 'Final Construction Fee' AND aml.matching_number IS NOT NULL
     ) AS subquery
     JOIN product_product ppd ON subquery.product_id = ppd.id
     JOIN account_analytic_account aaa ON aaa.id = subquery.analytic_account_id
     WHERE aaa.id IN (
         SELECT pp.analytical_account
         FROM pms_property pp
         WHERE pp.id = p.address
     )
    ) AS const_fee_final_paid_date

FROM 
    pms_projects p
LEFT JOIN 
    pms_property pp ON p.address = pp.id
LEFT JOIN 
    pms_county pc ON p.county = pc.id
LEFT JOIN 
    hr_employee he_pm ON p.project_manager = he_pm.id
LEFT JOIN 
    hr_employee he_zc ON p.zone_coordinator = he_zc.id
LEFT JOIN 
    hr_employee he_su ON p.superintendent = he_su.id
LEFT JOIN 
    pms_housemodels hm ON p.house_model = hm.id
LEFT JOIN 
    res_partner rp ON p.owner_property = rp.id
WHERE 
    p.address IS NOT NULL

    """



            