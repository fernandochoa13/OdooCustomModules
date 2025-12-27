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

class PropertyTimesReport(models.Model):
    _name = "property.times.report"
    _description = "Property Times Report"
    _auto = False

    id = fields.Integer(readonly=True)
    property_name = fields.Char(string='Property Name', readonly=True)
    house_model = fields.Char(string='House Model', readonly=True)
    construction_phase = fields.Char(string='Construction Phase', readonly=True)
    engineering_fee_duration = fields.Integer(string='Engineering Fee Duration (Days)', readonly=True)
    survey_issued_duration = fields.Integer(string='Survey Issued Duration (Days)', readonly=True)
    plot_plan_issued_duration = fields.Integer(string='Plot Plan Issued Duration (Days)', readonly=True)
    construction_draw_calc_duration = fields.Integer(string='Construction Drawing & Calc Duration (Days)', readonly=True)
    energy_calcs_duration = fields.Integer(string='Energy Calcs Duration (Days)', readonly=True)
    septic_permit_issue_duration = fields.Integer(string='Septic Permit Issued Duration (Days)', readonly=True)
    truss_calcs_duration = fields.Integer(string='Truss Calcs Duration (Days)', readonly=True)
    permit_pip_duration = fields.Integer(string='Permit PIP Duration (Days)', readonly=True)
    permit_applied_duration = fields.Integer(string='Permit Applied Duration (Days)', readonly=True)
    permit_issued_duration = fields.Integer(string='Permit Issued Duration (Days)', readonly=True)
    total_days = fields.Integer(string='Total Days Spent', readonly=True)

    @property
    def _table_query(self):
        return f"""
            WITH activity_durations AS (
                SELECT
                    prop.id AS id,
                    prop.name AS property_name,
                    house.name AS house_model,
                    proj.status_construction AS construction_phase,

                    -- engineering_fee_duration: Duración de la actividad 'engineering fee'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%engineering fee%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%engineering fee%%' THEN COALESCE(act.start_date, act.order_date) END)) AS engineering_fee_duration,
                    
                    -- survey_issued_duration: Duración de la actividad 'survey issued'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%survey issued%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%survey issued%%' THEN COALESCE(act.start_date, act.order_date) END)) AS survey_issued_duration,
                    
                    -- plot_plan_issued_duration: Duración de la actividad 'plot plan'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%plot plan%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%plot plan%%' THEN COALESCE(act.start_date, act.order_date) END)) AS plot_plan_issued_duration,
                    
                    -- construction_draw_calc_duration: Duración de la actividad 'construction drawing'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%construction drawing%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%construction drawing%%' THEN COALESCE(act.start_date, act.order_date) END)) AS construction_draw_calc_duration,

                    -- energy_calcs_duration: Duración de la actividad 'energy calc'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%energy calc%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%energy calc%%' THEN COALESCE(act.start_date, act.order_date) END)) AS energy_calcs_duration,

                    -- septic_permit_issue_duration: Duración de la actividad 'septic permit'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%septic permit%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%septic permit%%' THEN COALESCE(act.start_date, act.order_date) END)) AS septic_permit_issue_duration,

                    -- truss_calcs_duration: Duración de la actividad 'truss calcs'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%truss calcs%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%truss calcs%%' THEN COALESCE(act.start_date, act.order_date) END)) AS truss_calcs_duration,

                    -- permit_pip_duration: Duración de la actividad 'permit pip'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%permit pip%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%permit pip%%' THEN COALESCE(act.start_date, act.order_date) END)) AS permit_pip_duration,

                    -- permit_applied_duration: Duración de la actividad 'permit applied'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%permit applied%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%permit applied%%' THEN COALESCE(act.start_date, act.order_date) END)) AS permit_applied_duration,

                    -- permit_issued_duration: Duración de la actividad 'permit issued'
                    DATE_PART('day', MIN(CASE WHEN tmpl.name ILIKE '%%permit issued%%' THEN act.end_date END)
                                    - MIN(CASE WHEN tmpl.name ILIKE '%%permit issued%%' THEN COALESCE(act.start_date, act.order_date) END)) AS permit_issued_duration
                FROM
                    pms_property prop
                LEFT JOIN
                    pms_projects proj ON proj.address = prop.id
                LEFT JOIN
                    pms_projects_routes act ON act.project_property = proj.id
                LEFT JOIN
                    pms_projects_routes_templates_lines tmpl ON tmpl.id = act.name
                LEFT JOIN
                    pms_housemodels house ON house.id = prop.house_model
                GROUP BY
                    prop.id, prop.name, house.name, proj.status_construction, proj.create_date
            )

            SELECT
                id,
                property_name,
                house_model,
                construction_phase,
                engineering_fee_duration,
                survey_issued_duration,
                plot_plan_issued_duration,
                construction_draw_calc_duration,
                energy_calcs_duration,
                septic_permit_issue_duration,
                truss_calcs_duration,
                permit_pip_duration,
                permit_applied_duration,
                permit_issued_duration,
                (COALESCE(engineering_fee_duration, 0)
                + COALESCE(survey_issued_duration, 0)
                + COALESCE(plot_plan_issued_duration, 0)
                + COALESCE(construction_draw_calc_duration, 0)
                + COALESCE(energy_calcs_duration, 0)
                + COALESCE(septic_permit_issue_duration, 0)
                + COALESCE(truss_calcs_duration, 0)
                + COALESCE(permit_pip_duration, 0)
                + COALESCE(permit_applied_duration, 0)
                + COALESCE(permit_issued_duration, 0)) AS total_days
            FROM
                activity_durations
            ORDER BY
                property_name
        """


