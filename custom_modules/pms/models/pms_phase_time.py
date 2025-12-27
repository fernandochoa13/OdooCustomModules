from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from odoo.fields import Command
from datetime import date

class pms_phase_time(models.Model):
    _name = 'pms.phase.time'
    _description = 'Phase Time'
    _auto = False
    _rec_name = 'phases'

    id = fields.Integer(Readonly=True)
    duration = fields.Integer(string='Duration (Days)', readonly=True)
    start_date = fields.Datetime(string='Start Date', readonly=True)
    end_date = fields.Datetime(string='End Date', readonly=True)
    phases = fields.Selection(selection=[
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
        ], string="Construction Phase",
        readonly=True)
    project_id = fields.Many2one('pms.projects', string='Project', readonly=True)
    phase_order_index = fields.Integer(string='Phase Order', readonly=True)

    @property
    def _table_query(self):
        project = self.env.context.get('property_project')

        query = f"""
            SELECT
                min(pms_projects_routes.id) AS id,
                pms_projects_routes.project_property AS project_id,
                pms_projects_routes.phase AS phases,
                min(pms_projects_routes.start_date) AS start_date,
                max(pms_projects_routes.end_date) AS end_date,
                min(pms_projects_routes_templates_lines.sequence) AS sequenc,
                ROUND(EXTRACT(epoch FROM (max(pms_projects_routes.end_date) - min(pms_projects_routes.start_date)))/86400) AS duration,
                CASE pms_projects_routes.phase
                    WHEN 'epp' THEN 1
                    WHEN 'pip' THEN 2
                    WHEN 'pps' THEN 3
                    WHEN 'ppa' THEN 4
                    WHEN 'cop' THEN 5
                    WHEN 'cop1' THEN 6
                    WHEN 'cop2' THEN 7
                    WHEN 'cop3' THEN 8
                    WHEN 'cop4' THEN 9
                    WHEN 'coc' THEN 10
                    ELSE 99
                END as phase_order_index
            FROM
                pms_projects_routes
            LEFT JOIN
                pms_projects_routes_templates_lines ON pms_projects_routes.name = pms_projects_routes_templates_lines.id
        """

        if project:
            query += " WHERE pms_projects_routes.project_property = %s" % project

        query += f"""
            GROUP BY
                pms_projects_routes.phase,
                phase_order_index,
                pms_projects_routes.project_property
            ORDER BY
                pms_projects_routes.project_property,
                phase_order_index ASC,
                sequenc ASC
        """
        return query

    # @property
    # def _table_query(self):
    #     project_id = self.env.context.get('property_project')
    #     return"""
    #     SELECT min(pms_projects_routes.id) AS id,
	#     pms_projects_routes.phase AS phases,
	#     min(pms_projects_routes.start_date) AS start_date,
	#     max(pms_projects_routes.end_date) AS end_date,
	#     min(pms_projects_routes_templates_lines.sequence) AS sequenc,
	#     ROUND(EXTRACT(epoch FROM (min(pms_projects_routes.end_date) - max(pms_projects_routes.start_date)))/86400) AS duration
	   
    #     FROM pms_projects_routes

    #     LEFT JOIN pms_projects_routes_templates_lines ON pms_projects_routes.name = pms_projects_routes_templates_lines.id

    #     WHERE pms_projects_routes.project_property = %s

    #     GROUP BY pms_projects_routes.phase

    #     ORDER BY sequenc ASC
    #     """ % (project_id)




