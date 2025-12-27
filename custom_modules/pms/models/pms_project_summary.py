from odoo import api, models, tools, fields
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.fields import Command
from datetime import date

class pms_project_summary(models.Model):
    _name = "pms.project.summary"
    _description = "Table for Project Summary"
    _auto = False
    _rec_name = "name"

    # Fixed Readonly error: Readonly -> readonly

    id = fields.Integer(readonly=True)
    name = fields.Char(string="Activity Name", readonly=True)
    predecessor = fields.Char(string="Predecessors of route", readonly=True)
    activity_type = fields.Selection(selection=[("job", "Job"), ("payment", "Payment")], readonly=True)
    duration = fields.Integer(string="Work Days", readonly=True)
    phase = fields.Selection(selection=[
        ("epp", "EPP"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("ppa", "PPA"),
        ("cop", "COP"),
        ("cop1", "COP1"),
        ("cop2", "COP2"),
        ("cop3", "COP3"),
        ("cop4", "COP4"),
        ("coc", "COC")
        ], string="Construction Status", readonly=True)
    start_date = fields.Datetime(string="Start Date", readonly=True)
    order_date = fields.Datetime(string="Order Date", readonly=True)
    end_date = fields.Datetime(string="End Date", readonly=True)
    time_spent = fields.Integer(string="Days spent in activity", readonly=True)
    time_difference = fields.Integer(string="Days of difference", readonly=True)
    completed = fields.Boolean(string="Completed", readonly=True)
    sequence = fields.Integer(string="Sequence", readonly=True)

    @property
    def _table_query(self):
        project_id = self.env.context.get('property_project')
        project_route = self.env.context.get('project_route')
        return"""
                SELECT pms_projects_routes_templates_lines.id as id, pms_projects_routes.start_date as start_date, pms_projects_routes.order_date as order_date, pms_projects_routes.end_date as end_date, pms_projects_routes.time_spent as time_spent, pms_projects_routes.time_difference as time_difference, pms_projects_routes.completed as completed, pms_projects_routes_templates_lines.name as name, pms_projects_routes_templates_lines.predecessor as predecessor, pms_projects_routes_templates_lines.activity_type as activity_type, pms_projects_routes_templates_lines.duration as duration, pms_projects_routes_templates_lines.phase as phase, pms_projects_routes_templates_lines.sequence as sequence  
                            
                FROM pms_projects_routes_templates_lines
                            
                LEFT JOIN

                (SELECT pms_projects_routes.start_date, pms_projects_routes.order_date, pms_projects_routes.end_date, pms_projects_routes.time_spent, pms_projects_routes.time_difference, pms_projects_routes.completed, pms_projects_routes.name
                FROM pms_projects_routes
                WHERE pms_projects_routes.project_property = %s
                ) 

                pms_projects_routes ON pms_projects_routes_templates_lines.id = pms_projects_routes.name
                
                WHERE pms_projects_routes_templates_lines.route_header = %s

                """ % (project_id, project_route)
    
    
