from odoo import api, models, tools, fields
from datetime import datetime, time, timedelta
from datetime import date
import base64
import io


class VisitReports(models.Model):
    _name = 'visit.reports'
    _description = "Visit Reports"
    _auto = False

    id = fields.Integer(readonly=True)
    property_address = fields.Char(string="Planned Property")
    real_property = fields.Char(string="Real Property")
    project_phase = fields.Char(string="Project Phase")
    property_on_hold = fields.Boolean(string="Property On Hold")
    planned_visit_date = fields.Date(string="Planned Visit Date")
    planned_visitor = fields.Char(string="Planned Visitor")
    visit_date = fields.Date(string="Visit Date")
    visited_by = fields.Char(string="Visited By")

    @property
    def _table_query(self):
        start_date = self.env.context.get('start_date')
        end_date = self.env.context.get('end_date')

        return f"""
SELECT 
    row_number() OVER(ORDER BY pma1.id) as id, 
    pma1.name as property_address, 
    pma2.name as real_property, 
    COALESCE(proj1.status_construction, proj2.status_construction) as project_phase,
    COALESCE(pma1.on_hold, pma2.on_hold) as property_on_hold,
    sub1.planned_visit_date as planned_visit_date, 
    planned_name.name as planned_visitor, 
    sub2.visit_date as visit_date, 
    real_name.name as visited_by

FROM 
    (SELECT pms_planned_visit_days.id as id, pms_planned_visit_days.planned_property as planned_property, pms_planned_visit_days.planned_visit_date as planned_visit_date,
        pms_planned_visit_days.planned_visitor as planned_visitor
    FROM pms_planned_visit_days
    WHERE pms_planned_visit_days.planned_visit_date >= '{start_date}' AND pms_planned_visit_days.planned_visit_date <= '{end_date}') sub1
FULL JOIN 
    (SELECT pms_visit_days.property_name as property_name, pms_visit_days.visit_date as visit_date, pms_visit_days.visited_by as visited_by
    FROM pms_visit_days
    WHERE pms_visit_days.visit_date >= '{start_date}' AND pms_visit_days.visit_date <= '{end_date}') sub2 
ON sub1.planned_property = sub2.property_name
LEFT JOIN pms_property pma1 ON sub1.planned_property = pma1.id
LEFT JOIN pms_property pma2 ON sub2.property_name = pma2.id
LEFT JOIN pms_projects proj1 ON pma1.id = proj1.address
LEFT JOIN pms_projects proj2 ON pma2.id = proj2.address
LEFT JOIN hr_employee planned_name ON sub1.planned_visitor = planned_name.id
LEFT JOIN hr_employee real_name ON sub2.visited_by = real_name.id
"""



class VisitReportWizard(models.TransientModel):
    _name = 'visit.report.wizard'
    _description = 'Visit Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def generate_report(self):
        self.ensure_one()
        context = {
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'visit.reports.tree',
            'view_mode': 'tree',
            'res_model': 'visit.reports',
            'context': context,
        }