from odoo import fields, models, tools, api

class supervisor_inspections_report(models.Model):
    _name = 'supervisor.inspections.report'
    _description = 'Supervisor Inspections Report'
    _auto = False
    
    id = fields.Integer(string="id", readonly=True)
    owner_property = fields.Many2one('res.partner', string='Property Owner', readonly=True)
    address = fields.Many2one('pms.property', string='Address', readonly=True)
    county = fields.Many2one('pms.county', string='County', readonly=True)
    superintendent = fields.Many2one('hr.employee', string='Superintendent', readonly=True)
    project_manager = fields.Many2one('hr.employee', string='Project Manager', readonly=True)
    zone_coordinator  = fields.Many2one('hr.employee', string='Zone Coordinator', readonly=True)
    status_construction = fields.Selection(string="Construction Status", readonly=True, selection=[
        ("pending", "Pending"), ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"), ("pip", "PIP"),
        ("pps", "PPS"), ("ppa", "PPA"), ("cop", "COP"), ("cop1", "COP1"), ("cop2", "COP2"), ("cop3", "COP3"),
        ("cop4", "COP4"), ("cop5", "COP5"), ("coc", "COC"), ("completed", "Completed")])
    on_hold = fields.Boolean(string="On Hold", readonly=True)
    visit_day = fields.Selection( string="Visit Day", readonly=True, selection=[("monday", "Monday"), ("tuesday", "Tuesday"), 
        ("wednesday", "Wednesday"), ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday")])
    last_visit_day = fields.Date(string="Last Visit Day", readonly=True)
    
    next_activity_html = fields.Html(compute="_get_next_activity", string="Next Activity (HTML)", readonly=True)
    next_activity = fields.Char(compute="_get_next_activity", string="Next Activity (String)", readonly=True)
    
    upcoming_activity_html = fields.Html(compute="_get_upcoming_activities", string="Upcoming Activities (HTML)", readonly=True)
    upcoming_activity = fields.Char(compute="_get_upcoming_activities", string="Upcoming Activities (String)", readonly=True)
    
    pending_activity_html = fields.Html(compute="_get_job_activities", string="Pending Activities (HTML)", readonly=True)
    pending_activity = fields.Char(compute="_get_job_activities", string="Pending Activities (String)", readonly=True)
    
    last_activity_html = fields.Html(string="Last Activity (HTML)", readonly=True, compute="_get_last_activity")
    last_activity = fields.Html(string="Last Activity (String)", readonly=True, compute="_get_last_activity")
    
    own_third = fields.Selection(selection=[("own", "Own"), ("third", "Third")], readonly=True)
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)

    last_message_date = fields.Date(string="Last Message Date", readonly=True)
    last_message = fields.Text(string="Last Message (String)", readonly=True)
    last_message_html = fields.Html(string="Last Message (HTML)", compute="_last_message", readonly=True)
    
    @api.depends('last_message_date', 'last_message') # CREATES LAST MESSAGE HTML
    def _last_message(self):
        for record in self:
            if record.last_message:
                date = self.env['update.owner.call.day'].date_string(record.last_message_date.date())
                record.last_message_html = f'''{record.last_message}<strong>{date}</strong>'''
            else:
                record.last_message_html = f'No messages.'

    @api.depends('address')
    def _get_last_activity(self): # GET LAST ACTIVITY COMPLETED
        for record in self:
            string = ""
            reg_string = ""
            last_activities = self.env["pms.projects.routes"].search([
                ('address', '=', record.address.id),
                ('activity_type', '=', 'job'),
                ('end_date', '!=', False)  # Find activities with an end_date
            ], order='end_date DESC', limit=1)  # Order by end_date descending and get the first one

            if last_activities:
                last_activity = last_activities[0]
                reg_string = f"{last_activity.name.name} | "
                string = f"""
                    <div style="display: inline-block; width: max-content; padding: 0px 5px; margin: 1px; border-radius: 20px; 
                                border: 1.5px solid darkblue; background-color: lightblue; color: darkblue;">
                        <b>{last_activity.name.name}</b>
                    </div>
                    <br>
                """
            else:
                string = "None"
                reg_string = "None"

            record.last_activity_html = string
            record.last_activity = reg_string

    @api.depends('address') 
    def _get_next_activity(self): # GET NEXT ACTIVITY
        for record in self:
            string = ""
            reg_string = ""
            current_activity = self.env["pms.projects.routes"].search([
                ('address', '=', record.address.id),
                ('activity_type', '=', 'job'),
            ])
            if len(current_activity.ids) > 0:
                max_sequence = max(current_activity.mapped('sequence'))
                current_activity = current_activity.filtered_domain([('sequence', '=', max_sequence)])
                route_header = current_activity.mapped('name.route_header.id')[0]
                activity_sequence = current_activity.mapped('sequence')[0]
                next_activity = self.env["pms.projects.routes.templates.lines"].search([
                    ('route_header.id', '=', route_header),
                    ('sequence', '>', activity_sequence)
                ])
                if len(next_activity.ids) > 0:
                    min_sequence = min(next_activity.mapped('sequence'))
                    next_activity = next_activity.filtered_domain([('sequence', '=', min_sequence)])
                    for activity in next_activity:
                        reg_string += f"{activity.name} | "
                        string += f"""
                            <div style="display: inline-block; width: max-content; padding: 0px 5px; margin: 1px; border-radius: 20px; 
                                    border: 1.5px solid gray; background-color: white; color: gray">
                                <b>{activity.name}</b>
                            </div>
                            <br>
                        """
            record.next_activity_html = string
            record.next_activity = reg_string

        
    @api.depends('address') 
    def _get_job_activities(self): # GET JOB ACTIVITIES
        for record in self:
            string = ""
            reg_string = ""
            pending_activities = self.env["pms.projects.routes"].search([
                ('address', '=', record.address.id), 
                ('activity_type', '=', "job"),
                ('order_date', '!=', None),
                ('end_date', '=', None)
                ], order = 'time_difference ASC')
            if not pending_activities:
                record.pending_activity_html = "None"
            for act in pending_activities:
                if act.time_difference > 0:
                    bg_color = "lightgreen"
                    border_color = "darkgreen"
                    text_color = "black"
                elif act.time_difference == 0:
                    bg_color = "lightgray"
                    border_color = "gray"
                    text_color = "black"
                else:
                    bg_color = "lightcoral" 
                    border_color = "indianred" 
                    text_color = "white"

                reg_string = f"{act.duration}D {act.name.name} {act.time_difference}D | "
                string += f"""
                    <div style="display: inline-block; width: max-content; padding: 0px 5px; margin: 1px; border-radius: 20px; 
                            border: 1px solid {border_color}; background-color: {bg_color}; color: {text_color};">
                        <b>{act.duration}D {act.name.name} {act.time_difference}D</b>
                    </div>
                    <br> 
                """
            record.pending_activity_html = string
            record.pending_activity = reg_string
    
    @api.depends('address') 
    def _get_upcoming_activities(self): # GET UPCOMING JOB ACTIVITIES
        for record in self:
            string = ""
            reg_string = ""
            upcoming_activities = self.env["pms.projects.routes"].search([
                ('address', '=', record.address.id), 
                ('activity_type', '=', "job"),
                ('order_date', '=', None),
                ('end_date', '=', None)
                ], order = 'time_difference ASC', limit=3)
            if not upcoming_activities:
                record.upcoming_activity_html = "None"
            for act in upcoming_activities:
                if act.time_difference > 0:
                    bg_color = "lightgreen"
                    border_color = "darkgreen"
                    text_color = "black"
                elif act.time_difference == 0:
                    bg_color = "lightgray"
                    border_color = "gray"
                    text_color = "black"
                else:
                    bg_color = "lightcoral" 
                    border_color = "indianred" 
                    text_color = "white"

                reg_string += f"{act.duration}D {act.name.name} {act.time_difference}D | "
                string += f"""
                    <div style="display: inline-block; width: max-content; padding: 0px 5px; margin: 1px; border-radius: 20px; 
                            border: 1px solid {border_color}; background-color: {bg_color}; color: {text_color};">
                        <b>{act.duration}D {act.name.name} {act.time_difference}D</b>
                    </div>
                    <br> 
                """
            record.upcoming_activity_html = string
            record.upcoming_activity = reg_string

    def init(self):
        tools.drop_view_if_exists(self._cr, 'supervisor_inspections_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW supervisor_inspections_report AS (
                SELECT
                    pj.id as id,
                    pj.owner_property as owner_property,
                    pp.own_third AS own_third,
                    pj.county as county,
                    pj.superintendent as superintendent,
                    pj.project_manager as project_manager,
                    pp.on_hold as on_hold,
                    pj.zone_coordinator as zone_coordinator,
                    pj.status_construction as status_construction,
                    pj.visit_day as visit_day,
                    pj.last_visit_day as last_visit_day,
                    pj.issued_date AS issued_date,
                    pj.expiration_date AS expiration_date,
                    pj.address as address,
                    mmq.last_message_date AS last_message_date,
                    mmq.last_message AS last_message
                FROM pms_projects pj
                LEFT JOIN pms_property pp ON pj.address = pp.id
                LEFT JOIN (
                    SELECT
                        mm.date AS last_message_date,
                        max(mm.body) AS last_message,
                        mm.res_id
                    FROM mail_message mm
                    WHERE mm.model = 'pms.property' AND mm.date = (
                        SELECT
                            MAX(mm2.date)
                            FROM mail_message mm2
                            WHERE mm2.res_id = mm.res_id AND mm2.model = mm.model
                        )
                    GROUP BY mm.model, mm.res_id, mm.date
                ) mmq ON pj.address = mmq.res_id
            )
        """)
        
    def add_comment(self):
        active_ids = self.env.context.get('active_ids', [])
        records = self.env['supervisor.inspections.report'].browse(active_ids)
        properties = records.mapped('address').ids
        
        return {
            'name': 'Add Inspection Comment',
            'view_mode': 'form',
            'res_model': 'supervisor.comment',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'active_ids': properties,
            }
        }
        
class supervisor_comment(models.TransientModel):
    _name = 'supervisor.comment'
    _description = 'Supervisor Comment'

    comment = fields.Text(string="Comment", required=True)
    
    def create_comment(self):
        active_ids = self.env.context.get('active_ids', [])
        inspections = self.env['pms.property'].browse(active_ids)
        for inspection in inspections:
            inspection.message_post(body=self.comment)
        return {'type': 'ir.actions.act_window_close'}
