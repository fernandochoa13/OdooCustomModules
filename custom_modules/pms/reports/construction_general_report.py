from odoo import api, models, fields, tools, _
import logging
_logger = logging.getLogger(__name__)

class construction_general_report(models.Model):
    _name = "pms.construction.general.report"
    _description = "Construction General Report"
    _auto = False

    id = fields.Integer(readonly=True)
    county_id = fields.Many2one('pms.county', string="County", readonly=True)
    address_id = fields.Many2one('pms.property', string="Address", readonly=True)
    owner_property = fields.Many2one('res.partner', string = "Property Owner", readonly = True)
    superintendent_id = fields.Many2one('hr.employee', string="Superintendent", readonly=True)
    construction_status = fields.Selection(string="Construction Status", readonly=True, selection=[("pending", "Pending"), 
        ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"), ("pip", "PIP"), ("pps", "PPS"), ("ppa", "PPA"), ("cop", "COP"), 
        ("cop1", "COP1"), ("cop2", "COP2"), ("cop3", "COP3"), ("cop4", "COP4"), ("cop5", "COP5"), ("coc", "COC"), ("completed", "Completed")])

    last_visit = fields.Date(string="Last Visit", compute="_get_last_visit", readonly=True)
    on_hold = fields.Boolean(string="On Hold?", readonly=True)
    visit_day = fields.Selection(string="Visit Day", readonly=True, selection=[
        ("monday", "Monday"), ("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), 
        ("friday", "Friday"), ("saturday", "Saturday"), ("sunday", "Sunday"), ("any", "Any")])
    owner_call_day = fields.Selection(string="Owner Call Day", readonly=True, selection=[
        ("monday", "Monday"), ("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), 
        ("friday", "Friday"), ("saturday", "Saturday"), ("sunday", "Sunday"), ("any", "Any")])
    inspection_type = fields.Char(compute="_get_inspections", string="Inspections (String)", readonly=True)
    inspection_type_html = fields.Html(compute="_get_inspections", string="Inspections (HTML)", readonly=True)
    material_delivery = fields.Char(compute="_get_materials", string="Material Deliveries", readonly=True)
    last_message_date = fields.Date(string="Last Message Date", readonly=True)
    last_message = fields.Text(string="Last Message (String)", readonly=True)
    last_message_html = fields.Html(string="Last Message (HTML)", compute="_last_message", readonly=True)
    is_urgent = fields.Boolean(string="Urgent", readonly=True)
    
    payment_activity_html = fields.Html(compute="_get_payment_activities", string="Payment Activities (HTML)", readonly=True)
    payment_activity = fields.Char(compute="_get_payment_activities", string="Payment Activities (String)", readonly=True)
    
    pending_activity_html = fields.Html(compute="_get_job_activities", string="Pending Activities (HTML)", readonly=True)
    pending_activity = fields.Char(compute="_get_job_activities", string="Pending Activities (String)", readonly=True)
    
    own_third = fields.Selection(selection=[("own", "Own"), ("third", "Third")], readonly=True)
    estimated_cop2 = fields.Date(string="Estimated COP2 Date", readonly=True)
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)
    
    project_duration = fields.Integer(string="Project Duration (Days)", readonly=True, help="Estimated duration of the project in days.")
    
    @api.depends('address_id')
    def _get_payment_activities(self):
        for record in self:
            string = ""
            reg_string =""
            pending_payments = self.env["pms.projects.routes"].search([
                ('address', '=', record.address_id.id), 
                ('activity_type', '=', "payment"),
                ('order_date', '!=', None),
                ('end_date', '=', None)
                ], order = 'time_difference ASC')
            if not pending_payments: 
                record.payment_activity_html = "None" 
                record.payment_activity = "None"
                continue
            for act in pending_payments:
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
            record.payment_activity_html = string
            record.payment_activity = reg_string
    
    
    @api.depends('address_id')
    def _get_job_activities(self):
        for record in self:
            string = ""
            reg_string = ""
            pending_activities = self.env["pms.projects.routes"].search([
                ('address', '=', record.address_id.id), 
                ('activity_type', '=', "job"),
                ('order_date', '!=', None),
                ('end_date', '=', None)
                ], order = 'time_difference ASC')
            if not pending_activities: 
                record.pending_activity_html = "None" 
                record.pending_activity = "None"
                continue
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

                reg_string += f"{act.duration}D {act.name.name} {act.time_difference}D | "
                string += f"""
                    <div style="display: inline-block; width: max-content; padding: 0px 5px; margin: 1px; border-radius: 20px; 
                            border: 1px solid {border_color}; background-color: {bg_color}; color: {text_color};">
                        <b>{act.duration}D {act.name.name} {act.time_difference}D</b>
                    </div>
                    <br> 
                """
            record.pending_activity_html = string
            record.pending_activity = reg_string
    
    def change_owner_call_day(self): # OPENS CHANGE OWNER CALL DAY WIZARD
        return {
            'name': 'Change Owner Call Day',
            'view_mode': 'form',
            'res_model': 'update.owner.call.day',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def open_comments(self): # ACTION: OPEN COMMENTS
        return {
            'type': 'ir.actions.act_window',
            'name': 'pms_properties_view_form',
            'res_model': 'pms.property',
            'view_mode': 'form',
            'res_id': self.address_id.id
        }
    
    @api.depends('last_visit')
    def _get_last_visit(self): # TRANSFORMS LAST VISIT WITH DATE_STRING FUNCTION
        for record in self:
            project = self.env['pms.projects'].search([('address', '=', record.address_id.id)])
            record.last_visit = project.last_visit_day
    
    @api.depends('last_message_date', 'last_message') # CREATES LAST MESSAGE HTML
    def _last_message(self):
        for record in self:
            if record.last_message:
                date = self.env['update.owner.call.day'].date_string(record.last_message_date.date())
                record.last_message_html = f'''{record.last_message}<strong>{date}</strong>'''
            else:
                record.last_message_html = f'No messages.'

    @api.depends('address_id') # GET INSPECTIONS
    def _get_inspections(self):
        for record in self:
            insp_cnt_ordered = self.env["pms.inspections"].search_count([
                ('address', '=', record.address_id.id),
                ('status', '=', 'ordered')
            ])
            insp_cnt_failed = self.env["pms.inspections"].search_count([
                ('address', '=', record.address_id.id),
                ('status', '=', 'failed')
            ])
            insp_cnt_passed_after = self.env["pms.inspections"].search_count([
                ('address', '=', record.address_id.id),
                ('status', '=', 'passed_after')
            ])
            insp_cnt_passed = self.env["pms.inspections"].search_count([
                ('address', '=', record.address_id.id),
                ('status', '=', 'passed')
            ])
            total_inspections = insp_cnt_ordered + insp_cnt_failed + insp_cnt_passed_after + insp_cnt_passed
            if total_inspections == 0:
                record.inspection_type_html = "SIP"
                record.inspection_type = "SIP"
            else:
                record.inspection_type_html = f'''
                        {insp_cnt_ordered}&nbsp;Ordered<br>
                        {insp_cnt_passed}&nbsp;Passed<br>
                        {insp_cnt_failed}&nbsp;Failed<br>
                        {insp_cnt_passed_after}&nbsp;Passed&nbsp;after<br>&nbsp;&nbsp;&nbsp;Re-Inspection
                '''
                record.inspection_type = f'''{insp_cnt_ordered} Ordered. {insp_cnt_passed} Passed. {insp_cnt_failed} Failed. {insp_cnt_passed_after} Passed after Re-Inspection'''

    @api.depends('address_id')  # GET MATERIAL DELIVERY REPORT
    def _get_materials(self):
        for record in self:
            ordered_count = self.env["pms.materials"].search_count([
                ('property_id', '=', record.address_id.id),
                ('order_status', '=', 'ordered')
            ])
            # record.material_delivery_html = f'''<i>{ordered_count}&nbsp;Ordered<br></i>'''
            record.material_delivery = f"{ordered_count} Ordered"
        
    
    def change_urgent(self):
        projects = self.env.context.get('active_ids')
        updated = []
        if not projects:
            return self.env['update.owner.call.day'].simple_notification("error", "Error", "Unable to find any records to update.", False)
            
        for project in projects:
            selected_project = self.env['pms.projects'].browse(project)
            if not selected_project: continue
            
            property = self.env['pms.property'].browse(selected_project.address.id)
            if not property: continue
            property.update({'is_urgent': not property.is_urgent})
            updated.append(property)

        if len(updated) > 1: message = "%s properties' urgent status updated." % len(updated)
        else: message = "Property urgent status updated."
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': message, 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
        }
    
            
            
    def init(self):
        tools.drop_view_if_exists(self._cr, 'pms_construction_general_report')
        # Force update of Selection field metadata to include COP5
        # This ensures that 'cop5' value is recognized by Odoo's Selection field
        self._cr.execute("""
            CREATE OR REPLACE VIEW pms_construction_general_report AS (
                SELECT                          
                    p.id AS id,
                    p.county AS county_id,
                    p.address AS address_id,
                    p.estimated_cop2 AS estimated_cop2,
                    p.project_duration AS project_duration,
                    p.issued_date AS issued_date,
                    p.expiration_date AS expiration_date,
                    pp.on_hold AS on_hold,
                    pp.is_urgent AS is_urgent,
                    p.owner_property AS owner_property,
                    pp.own_third AS own_third,
                    p.superintendent AS superintendent_id,
                    p.status_construction AS construction_status,
                    rp.call_day AS owner_call_day,
                    p.visit_day AS visit_day,
                    mmq.last_message_date AS last_message_date,
                    mmq.last_message AS last_message
                FROM pms_projects p
                LEFT JOIN pms_property pp ON p.address = pp.id
                LEFT JOIN res_partner rp ON p.owner_property = rp.id
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
                ) mmq ON p.address =  mmq.res_id
            )
        """)
                # LEFT JOIN pms_projects_routes ppr ON p.address = ppr.address

####################################################################################################################################################################################################################################################################################################################################################################
############################### TransientModel para cambiar el dia de llamada del propietario #####################################################################################################################################################################################################################################################################
####################################################################################################################################################################################################################################################################################################################################################################

class update_owner_call_day(models.TransientModel):
    _name = "update.owner.call.day"
    _description = "Update Owner Call Day"
    
    owner_call_day = fields.Selection(string="Owner Call Day", default="None", required=True, selection=[
        ("monday", "Monday"), ("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), 
        ("friday", "Friday"), ("saturday", "Saturday"), ("sunday", "Sunday"), ("any", "Any")])
    
    def date_string(self, date): # FUNCTION TO TRANSFORM DATES TO A MORE READABLE FORMAT
        if date:
            days_ago = (fields.Date.today() - date).days
            if days_ago == fields.Date.today(): return 'Today'
            if days_ago == 1: return 'Yesterday'
            elif days_ago <= 7 and days_ago > 1: return f"{days_ago} days ago"
            else: return date.strftime('%m/%d/%Y')
        else: return 'None'
    
    def simple_notification(self, type, title, message, sticky): # FUNCTION TO SEND ERRORS AND WARNINGS AS NOTIFICATIONS
        notification = { "type": type, "message": _(message), "sticky": sticky }
        if title: notification["title"] = title
        self.env["bus.bus"]._sendone(self.env.user.partner_id, "simple_notification", notification)

    def update_owner_call_day(self):
        projects = self.env.context.get('active_ids')
        partner = None
        owners = []
        
        if not projects:
            return self.simple_notification("error", "Error", "Unable to find any records to update.", False)

        for project in projects:
            selected_project = self.env['pms.projects'].browse(project)

            if not selected_project:
                continue

            if not selected_project.owner_property:
                continue

            partner = selected_project.owner_property

            partner.update({'call_day': self.owner_call_day})
            owners.append(partner.name)

        if len(owners) > 1:
            message = "The call day for the %s selected owners was updated to: %s." % (len(owners), str(self.owner_call_day).title())
        elif partner:
            message = "%s\'s call day updated to: %s." % (partner.name, str(self.owner_call_day).title())
        else:
            message = "No owners were updated."

        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': message, 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
        }
        

        

    

