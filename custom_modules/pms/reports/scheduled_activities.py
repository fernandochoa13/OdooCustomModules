from odoo import api, models, tools, fields
from datetime import datetime, time, timedelta
from datetime import date
import base64
import io
from odoo import api, models, fields

from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning



class pms_schedule_activities(models.Model):
    _name = 'pms.schedule.activities'
    _description = "Activities Schedule"
    _auto = False
    _rec_name = 'display_name'

    id = fields.Integer(readonly=True)
    display_name = fields.Char(readonly=True, compute="_display_name")
    activity_name = fields.Char(readonly=True)
    activity_id = fields.Integer(readonly=True)
    address = fields.Char(readonly=True)
    start_date = fields.Date(readonly=True, compute="_schedule")
    end_date = fields.Date(readonly=True, compute="_schedule")
    project_manager = fields.Char(readonly=True)
    superintendent = fields.Char(readonly=True)
    zone_coordinator = fields.Char(readonly=True)
    county = fields.Char(readonly=True)
    owner = fields.Char(readonly=True)
    phase = fields.Char(readonly=True)
    duration = fields.Integer(readonly=True)

    def _display_name(self):
        for record in self:
            record.display_name = f'{record.address} - {record.activity_name}'

    def _schedule(self):
        # calculate end_date in the few ones that are
        for record in self:
            if record.start_date != '':
                record.end_date = record.start_date + timedelta(days=record.duration)

        # get list of activities completeders and with previous sequence and ones with end_Date
        
        
        # get relation with activities and their predecessors


        while '' in self.search([]).mapped("start_date"):
            pass
            # check if predecessors in list of completed
            # get activities with all predecessors completed
            # assign as start_date, max end_date in table
            # calculate end_date
            # add to list of activities completed

            



    @property
    def _table_query(self):
        today = date.today()
        return f"""
SELECT ROW_NUMBER() OVER (ORDER BY pms_projects.id) AS id, pms_property.name as address, pms_county.name as county, empl1.name as project_manger, empl2.name as superintendent,
empl3.name as zone_coordinator, pms_projects.starting_activity as starting_activity,
pms_projects_routes_templates_lines.name as activity_name,pms_projects_routes_templates_lines.id as activity_id, pms_projects_routes_templates_lines.phase as phase,
MAX(CASE
WHEN CONCAT_WS('-', pms_projects.id, pms_projects_routes_templates_lines.id) IN
(
SELECT sub2.activity_name
FROM
(SELECT sub1.activity_name, 
SUM(CASE WHEN (sub1.predecessor_completed = 'True' OR (sub1.predecessor_completed IS NULL AND (sub1.strt_sequence > sub1.predec_sequence)))
THEN 1
ELSE 0
END) AS predecessor_completed,
COUNT(*) AS predecessor_count
FROM (SELECT CONCAT_WS('-', pms_projects.id, pms_projects_routes_templates_lines.id) AS activity_name,
 predec_complete.completed as predecessor_completed, predec_sequence.sequence as predec_sequence, starting_actsq.sequence as strt_sequence

FROM pms_projects
LEFT JOIN pms_projects_routes_templates_lines AS starting_actsq ON pms_projects.starting_activity = starting_actsq.id

INNER JOIN pms_projects_routes_templates_lines ON pms_projects.project_routes = pms_projects_routes_templates_lines.route_header

LEFT JOIN pms_projects_routes ON pms_projects_routes_templates_lines.id = pms_projects_routes.name AND
pms_projects.id = pms_projects_routes.project_property

LEFT JOIN pms_projects_routes_templates_lines_predecessor_rel ON pms_projects_routes_templates_lines.id = pms_projects_routes_templates_lines_predecessor_rel.route_line_id

LEFT JOIN pms_projects_routes AS predec_complete ON pms_projects_routes_templates_lines_predecessor_rel.predecessor_id = pms_projects_routes.name AND
pms_projects.id = pms_projects_routes.project_property

LEFT JOIN pms_projects_routes_templates_lines AS predec_sequence ON predec_complete.name = predec_sequence.id
	  
WHERE pms_projects.status_construction != 'coc' AND 
(pms_projects_routes_templates_lines.sequence > starting_actsq.sequence OR pms_projects.starting_activity IS NULL)
AND (pms_projects_routes.completed = 'False' OR pms_projects_routes.completed IS NULL) )sub1
	  
GROUP BY sub1.activity_name) sub2

WHERE sub2.predecessor_completed = sub2.predecessor_count)

THEN '{today}'
ELSE ''
END)
AS start_date,

pms_projects_routes_templates_lines.duration as duration,
NULL as end_date
NULL as display_name

FROM pms_projects

LEFT JOIN pms_property ON pms_projects.address = pms_property.id

LEFT JOIN pms_county ON pms_projects.county = pms_county.id

LEFT JOIN hr_employee as empl1 ON pms_projects.project_manager = empl1.id

LEFT JOIN hr_employee as empl2 ON pms_projects.superintendent = empl2.id

LEFT JOIN hr_employee as empl3 ON pms_projects.zone_coordinator = empl3.id

LEFT JOIN res_partner ON pms_projects.owner_property = res_partner.id

LEFT JOIN pms_projects_routes_templates_lines AS starting_actsq ON pms_projects.starting_activity = starting_actsq.id

INNER JOIN pms_projects_routes_templates_lines ON pms_projects.project_routes = pms_projects_routes_templates_lines.route_header

LEFT JOIN pms_projects_routes ON pms_projects_routes_templates_lines.id = pms_projects_routes.name AND
pms_projects.id = pms_projects_routes.project_property

LEFT JOIN pms_projects_routes_templates_lines_predecessor_rel ON pms_projects_routes_templates_lines.id = pms_projects_routes_templates_lines_predecessor_rel.route_line_id

LEFT JOIN pms_projects_routes AS predec_complete ON pms_projects_routes_templates_lines_predecessor_rel.predecessor_id = pms_projects_routes.name AND
pms_projects.id = pms_projects_routes.project_property

WHERE pms_projects.status_construction != 'coc' AND 
(pms_projects_routes_templates_lines.sequence > starting_actsq.sequence OR pms_projects.starting_activity IS NULL)
AND (pms_projects_routes.completed = 'False' OR pms_projects_routes.completed IS NULL)

GROUP BY pms_property.name, pms_county.name, empl1.name, empl2.name,
empl3.name, pms_projects.starting_activity,
pms_projects_routes_templates_lines.name, pms_projects_routes_templates_lines.phase, pms_projects_routes_templates_lines.duration
"""