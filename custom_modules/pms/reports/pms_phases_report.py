from odoo import models, fields, api

class pms_phases_report(models.Model):
    _name = 'pms.phases.report'
    _description = 'Project Phases Report'
    _auto = False
    
    project_id = fields.Many2one('pms.projects', string='Project', readonly=True)
    county = fields.Many2one("pms.county", string='County', readonly=True)
    superintendent = fields.Many2one('hr.employee', string='Superintendent', readonly=True)
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)

    # Individual Phase Durations
    cop_days = fields.Integer(string='COP DAYS', readonly=True)
    cop1_days = fields.Integer(string='COP1 DAYS', readonly=True)
    cop2_days = fields.Integer(string='COP2 DAYS', readonly=True)
    cop3_days = fields.Integer(string='COP3 DAYS', readonly=True)
    cop4_days = fields.Integer(string='COP4 DAYS', readonly=True)
    cop5_days = fields.Integer(string='COP5 DAYS', readonly=True)

    # KPIs
    kpi1 = fields.Integer(string='KPI1', readonly=True)
    kpi2 = fields.Integer(string='KPI2', readonly=True)
    kpi3 = fields.Integer(string='KPI3', readonly=True)

    total_days = fields.Integer(string='Total Days', readonly=True)


    @property
    def _table_query(self):
        return """
            SELECT
                MIN(pp.id) AS id,
                pp.id AS project_id,
                pp.county AS county,
                pp.superintendent AS superintendent,
                pp.issued_date AS issued_date,
                pp.expiration_date AS expiration_date,
                SUM(CASE WHEN ppr.phase = 'cop' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS cop_days,
                SUM(CASE WHEN ppr.phase = 'cop1' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS cop1_days,
                SUM(CASE WHEN ppr.phase = 'cop2' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS cop2_days,
                SUM(CASE WHEN ppr.phase = 'cop3' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS cop3_days,
                SUM(CASE WHEN ppr.phase = 'cop4' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS cop4_days,
                SUM(CASE WHEN ppr.phase = 'cop5' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS cop5_days,

                SUM(CASE WHEN ppr.phase IN ('cop', 'cop1') THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS kpi1,

                SUM(CASE WHEN ppr.phase = 'cop2' THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS kpi2,

                SUM(CASE WHEN ppr.phase IN ('cop3', 'cop4', 'cop5') THEN ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400) ELSE 0 END) AS kpi3,
                
                SUM(
                    ROUND(EXTRACT(epoch FROM (ppr.end_date - ppr.start_date))/86400)
                ) AS total_days
                
            FROM pms_projects pp
            LEFT JOIN pms_projects_routes ppr ON pp.id = ppr.project_property
            GROUP BY pp.id, pp.name
            ORDER BY pp.name
        """