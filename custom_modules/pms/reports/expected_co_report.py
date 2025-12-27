from odoo import api, fields, models, _

from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class expected_co_report_wizard(models.TransientModel):
    _name = 'expectedco.wizard'
    _description = 'Expected CO Wizard'

    status_construction = fields.Selection(string="Construction Status", default='cop4', required=True,
        selection=[
            ("pending", "Pending"),
            ("pip", "PIP"),
            ("pps", "PPS"),
            ("epp", "EPP"),
            ("pip", "PIP"),
            ("pps", "PPS"),
            ("ppa", "PPA"),
            ("cop", "COP"),
            ("cop1", "COP1"),
            ("cop2", "COP2"),
            ("cop3", "COP3"),
            ("cop4", "COP4"),
            ("cop5", "COP5"),
            ("coc", "COC"),
            ("completed", "Completed"),
        ])
    month = fields.Selection(string="Month", required=True, default=lambda self: str((datetime.now().month % 12) + 1),
        selection=[
            ('1', 'January'),
            ('2', 'February'),
            ('3', 'March'),
            ('4', 'April'),
            ('5', 'May'),
            ('6', 'June'),
            ('7', 'July'),
            ('8', 'August'),
            ('9', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December')
        ])
        
    def open_report(self):
        month_name = dict(self._fields['month'].selection).get(self.month)
        status_name = dict(self._fields['status_construction'].selection).get(self.status_construction)
        return {
            'name': f'Expected CO Report: {month_name}, {status_name}',
           'type': 'ir.actions.act_window',
           'res_model': 'expectedco.report',
           'view_mode': 'tree',
           'target': 'current',
           'context': {
                'default_status_construction': self.status_construction,
                'default_month': self.month,
               }
       }


class ExpectedCOReport(models.Model):
    _name = "expectedco.report"
    _description = "Expected CO Report"
    _auto = False

    id = fields.Integer('ID', readonly=True)
    project_name = fields.Char('Property', readonly=True)
    incomplete_activities = fields.Char('Missing Activities', readonly=True)
    expected_co_date = fields.Date('Expected CO Date', readonly=True)
    # project_id = fields.Many2one('pms.projects', string='Project', readonly=True)
    county = fields.Many2one("pms.county", string="County", readonly=True)
    own_third_property = fields.Selection(string="Own/Third", selection=[("own", "Own"), ("third", "Third")], readonly=True)
    total_duration = fields.Integer('Total Duration (Days)', readonly=True)  # New field
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)

    


    @property
    def _table_query(self):
        status_construction = self.env.context.get('default_status_construction')
        month = self.env.context.get('default_month')

        return f"""
            SELECT
                proj.id AS id,
                proj.name AS project_name,
                STRING_AGG(tmpl_line.name || ' (' || tmpl_line.duration || ' days)', ', ') AS incomplete_activities,
                (CURRENT_DATE + INTERVAL '1 day' * COALESCE(SUM(tmpl_line.duration), 0)) AS expected_co_date,
                SUM(tmpl_line.duration) AS total_duration, -- Calculate total duration
                proj.issued_date AS issued_date,
                proj.expiration_date AS expiration_date,
                pp.county AS county,
                pp.own_third AS own_third_property
            FROM
                pms_projects proj
            JOIN
                pms_projects_routes_templates route_template ON route_template.id = proj.project_routes
            JOIN
                pms_projects_routes_templates_lines tmpl_line ON tmpl_line.route_header = route_template.id
            LEFT JOIN
                pms_projects_routes act ON act.project_property = proj.id AND act.name = tmpl_line.id
            JOIN
                pms_property pp ON pp.id = proj.address
            WHERE
                (act.id IS NULL OR act.completed = FALSE)
                AND proj.status_construction ILIKE '{status_construction}'
                AND EXTRACT(MONTH FROM proj.expected_co_date) = {month}
                AND tmpl_line.add_to_report = TRUE
            GROUP BY
                proj.id, proj.name, pp.county, pp.own_third
            ORDER BY
                proj.name
        """

# CURRENT QUERY

    # @property
    # def _table_query(self):
    #     status_construction = self.env.context.get('default_status_construction')
    #     month = self.env.context.get('default_month')

    #     return f"""
    #         SELECT
    #             proj.id AS id,
    #             proj.name AS project_name,
    #             STRING_AGG(tmpl_line.name, ', ') AS incomplete_activities,
    #             proj.expected_co_date AS expected_co_date,
    #             pp.county AS county,
    #             pp.own_third AS own_third_property
    #         FROM
    #             pms_projects proj
    #         JOIN
    #             pms_projects_routes_templates route_template ON route_template.id = proj.project_routes
    #         JOIN
    #             pms_projects_routes_templates_lines tmpl_line ON tmpl_line.route_header = route_template.id
    #         LEFT JOIN
    #             pms_projects_routes act ON act.project_property = proj.id AND act.name = tmpl_line.id
    #         LEFT JOIN 
    #             (
    #                 SELECT 
    #                     project_property, 
    #                     MAX(tmpl_line.sequence) AS max_completed_sequence
    #                 FROM 
    #                     pms_projects_routes act
    #                 JOIN 
    #                     pms_projects_routes_templates_lines tmpl_line ON act.name = tmpl_line.id
    #                 WHERE 
    #                     act.completed = TRUE
    #                 GROUP BY 
    #                     project_property
    #             ) AS completed_sequences
    #             ON completed_sequences.project_property = proj.id
    #         JOIN
    #             pms_property pp ON pp.id = proj.address
    #         WHERE
    #             (act.id IS NULL OR act.completed = FALSE)
    #             AND (completed_sequences.max_completed_sequence IS NULL OR tmpl_line.sequence > completed_sequences.max_completed_sequence)
    #             AND proj.status_construction ILIKE '{status_construction}' -- Filter by project status_construction
    #             AND EXTRACT(MONTH FROM proj.expected_co_date) = {month}
    #             AND tmpl_line.add_to_report = TRUE
    #         GROUP BY
    #             proj.id, proj.name, proj.expected_co_date, pp.county, pp.own_third
    #         ORDER BY
    #             proj.name
    #     """
        
        

# PREVIOUS QUERY

    # @property
    # def _table_query(self):
    #     return f"""
    #         SELECT
    #             proj.id AS id,
    #             proj.name AS project_name,
    #             STRING_AGG(tmpl_line.name, ', ') AS incomplete_activities,
    #             (CURRENT_DATE + INTERVAL '1 day' * COALESCE(SUM(duration_by_predecessor.max_duration), 0)) AS expected_co_date
    #         FROM
    #             pms_projects proj
    #         JOIN
    #             pms_projects_routes_templates route_template ON route_template.id = proj.project_routes
    #         JOIN
    #             pms_projects_routes_templates_lines tmpl_line ON tmpl_line.route_header = route_template.id
    #         LEFT JOIN
    #             pms_projects_routes act ON act.project_property = proj.id AND act.name = tmpl_line.id
    #         LEFT JOIN
    #             (
    #                 SELECT
    #                     pred_rel.route_line_id AS activity_id,
    #                     tmpl_lines.route_header AS route_header,
    #                     MAX(tmpl_lines.duration) AS max_duration
    #                 FROM
    #                     pms_projects_routes_templates_lines tmpl_lines
    #                 JOIN
    #                     pms_projects_routes_templates_lines_predecessor_rel pred_rel 
    #                     ON tmpl_lines.id = pred_rel.predecessor_id
    #                 WHERE
    #                     tmpl_lines.phase ILIKE 'COP4' AND tmpl_lines.add_to_report = TRUE
    #                 GROUP BY
    #                     pred_rel.route_line_id, tmpl_lines.route_header
    #             ) AS duration_by_predecessor 
    #             ON duration_by_predecessor.route_header = tmpl_line.route_header
    #             AND duration_by_predecessor.activity_id = tmpl_line.id
    #         LEFT JOIN 
    #             (
    #                 SELECT 
    #                     project_property, 
    #                     MAX(tmpl_line.sequence) AS max_completed_sequence
    #                 FROM 
    #                     pms_projects_routes act
    #                 JOIN 
    #                     pms_projects_routes_templates_lines tmpl_line ON act.name = tmpl_line.id
    #                 WHERE 
    #                     act.completed = TRUE
    #                 GROUP BY 
    #                     project_property
    #             ) AS completed_sequences
    #             ON completed_sequences.project_property = proj.id
    #         WHERE
    #             (act.id IS NULL OR act.completed = FALSE)
    #             AND (completed_sequences.max_completed_sequence IS NULL OR tmpl_line.sequence > completed_sequences.max_completed_sequence)
    #             AND proj.id = {self.env.context.get('default_property_id')}
    #             AND tmpl_line.phase ILIKE 'COP4' AND tmpl_line.add_to_report = TRUE
    #         GROUP BY
    #             proj.id
    #         ORDER BY
    #             proj.name
    #     """
        
        
        # UNUSED QUERY TO UPDATE EXPECTED CO DATES IN PROJECTS

    # @api.model
    # def update_expected_co_dates(self):
    #     query = """
    #         SELECT
    #             proj.id AS id,
    #             (CURRENT_DATE + INTERVAL '1 day' * COALESCE(SUM(duration_by_predecessor.max_duration), 0)) AS expected_co_date
    #         FROM
    #             pms_projects proj
    #         JOIN
    #             pms_projects_routes_templates route_template ON route_template.id = proj.project_routes
    #         JOIN
    #             pms_projects_routes_templates_lines tmpl_line ON tmpl_line.route_header = route_template.id
    #         LEFT JOIN
    #             pms_projects_routes act ON act.project_property = proj.id AND act.name = tmpl_line.id
    #         LEFT JOIN
    #             (
    #                 SELECT
    #                     pred_rel.route_line_id AS activity_id,
    #                     tmpl_lines.route_header AS route_header,
    #                     MAX(tmpl_lines.duration) AS max_duration
    #                 FROM
    #                     pms_projects_routes_templates_lines tmpl_lines
    #                 JOIN
    #                     pms_projects_routes_templates_lines_predecessor_rel pred_rel 
    #                     ON tmpl_lines.id = pred_rel.predecessor_id
    #                 WHERE
    #                     tmpl_lines.phase ILIKE 'COP4' AND tmpl_lines.add_to_report = TRUE
    #                 GROUP BY
    #                     pred_rel.route_line_id, tmpl_lines.route_header
    #             ) AS duration_by_predecessor 
    #             ON duration_by_predecessor.route_header = tmpl_line.route_header
    #             AND duration_by_predecessor.activity_id = tmpl_line.id
    #         LEFT JOIN 
    #             (
    #                 SELECT 
    #                     project_property, 
    #                     MAX(tmpl_line.sequence) AS max_completed_sequence
    #                 FROM 
    #                     pms_projects_routes act
    #                 JOIN 
    #                     pms_projects_routes_templates_lines tmpl_line ON act.name = tmpl_line.id
    #                 WHERE 
    #                     act.completed = TRUE
    #                 GROUP BY 
    #                     project_property
    #             ) AS completed_sequences
    #             ON completed_sequences.project_property = proj.id
    #         WHERE
    #             (act.id IS NULL OR act.completed = FALSE)
    #             AND (completed_sequences.max_completed_sequence IS NULL OR tmpl_line.sequence > completed_sequences.max_completed_sequence)
    #             AND tmpl_line.phase ILIKE 'COP4' AND tmpl_line.add_to_report = TRUE
    #         GROUP BY
    #             proj.id
    #     """
    #     self.env.cr.execute(query)
    #     results = self.env.cr.fetchall()
    #     for project_id, expected_co_date in results:
    #         project = self.env['pms.projects'].browse(project_id)
    #         project.write({'expected_co_date': expected_co_date})
