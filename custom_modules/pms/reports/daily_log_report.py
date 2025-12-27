from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch

from odoo import api, fields, models, _, Command, tools
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference



from odoo import models, fields, tools

from odoo import models, fields, tools

class PmsDailyLogReport(models.Model):
    _name = "pms.daily.log.report"
    _description = "Daily Log Report"
    _auto = False

    id = fields.Integer(readonly=True)
    date = fields.Date(string='Date', readonly=True)
    author = fields.Char(string='Author', readonly=True)
    subject_id = fields.Char(string='Subject', readonly=True)
    doc_model = fields.Char(string='Document Model', readonly=True)
    doc_id = fields.Integer(string='Document ID', readonly=True)
    body_message = fields.Html(string='Body', readonly=True)
    property_id = fields.Integer(string='Property ID', readonly=True)
    property_name = fields.Char(string='Property', readonly=True)
    county_id = fields.Integer(string='County ID', readonly=True)
    county_name = fields.Char(string='County', readonly=True)
    partner_id = fields.Integer(string='Partner ID', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    superintendent_name = fields.Char(string='Superintendent', readonly=True)
    zone_coordinator_name = fields.Char(string='Zone Coordinator', readonly=True)
    project_manager_name = fields.Char(string='Project Manager', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'pms_daily_log_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW pms_daily_log_report AS (
                WITH project_details AS (
                    SELECT 
                        address, 
                        MAX(CASE WHEN pr.superintendent IS NOT NULL THEN e1.name END) AS superintendent_name,
                        MAX(CASE WHEN pr.zone_coordinator IS NOT NULL THEN e2.name END) AS zone_coordinator_name,
                        MAX(CASE WHEN pr.project_manager IS NOT NULL THEN e3.name END) AS project_manager_name
                    FROM pms_projects pr
                    LEFT JOIN hr_employee e1 ON pr.superintendent = e1.id
                    LEFT JOIN hr_employee e2 ON pr.zone_coordinator = e2.id
                    LEFT JOIN hr_employee e3 ON pr.project_manager = e3.id
                    GROUP BY address
                )
                SELECT DISTINCT
                    mm.id,
                    mm.date,
                    rp.name AS author,
                    mm.subject AS subject_id,
                    mm.model AS doc_model,
                    mm.res_id AS doc_id,
                    mm.body AS body_message,
                    p.id AS property_id,
                    p.name AS property_name,
                    p.county AS county_id,
                    pc.name AS county_name,
                    rp.id AS partner_id,
                    rp.name AS partner_name,
                    pd.superintendent_name,
                    pd.zone_coordinator_name,
                    pd.project_manager_name
                FROM mail_message mm
                JOIN pms_property p ON mm.res_id = p.id
                JOIN res_partner rp ON mm.author_id = rp.id
                JOIN pms_county pc ON p.county = pc.id
                LEFT JOIN project_details pd ON p.id = pd.address
                WHERE mm.model = 'pms.property' AND mm.is_internal IS NOT TRUE
            )
        """)


    def view_document(self):
        if self.doc_model == 'pms.property':
            return {
                'type': 'ir.actions.act_window',
                'name': ('pms_properties_view_form'),
                'res_model': 'pms.property',
                'view_mode': 'form',
                'res_id': self.property_id}
