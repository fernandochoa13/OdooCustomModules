import base64
from odoo import api, models, fields
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo import api, fields, models, Command, _
from datetime import datetime, time, timedelta
from odoo.fields import Command
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)
                

class pms_projects_routes(models.Model):
    _name = "pms.projects.routes"
    _description = "Table for Property Project Management Routes"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    # Project Property
    project_property = fields.Many2one("pms.projects", string="Project Property", required=True, default=lambda self: self._default_project_property())   
    project_routes = fields.Integer(string="Project Route", readonly=True)
    visit_day = fields.Selection(related="project_property.visit_day", string="Visit Day", readonly=True, store=True)
    project_manager = fields.Many2one(related="project_property.project_manager", string="Project Manager", readonly=True, store=True)
    county = fields.Many2one(related="project_property.county", string="County", readonly=True, store=True)
    address = fields.Many2one(related="project_property.address", string="Property", readonly=True, store=True)
    owner_property = fields.Many2one(related="project_property.owner_property", readonly=True, string="Owner", store=True)
    house_model = fields.Many2one(related="project_property.house_model", readonly=True, string="House Model", store=True)
    on_hold = fields.Boolean(string="On Hold", compute="_compute_on_hold", readonly=True, store=True)
    # Job Details
    name = fields.Many2one("pms.projects.routes.templates.lines", string="Activity Name", required=True, domain="[('route_header', '=', project_routes)]")
    product = fields.Many2one("product.product", string="Job Name", related="name.product", store=True)
    activity_type = fields.Selection(related="name.activity_type", store=True) # ignores selection as its related: selection=[("job", "Job"), ("payment", "Payment")],
    sequence = fields.Integer(related="name.sequence", store=True) # changed Store to store
    duration = fields.Integer(string="Work Days", related="name.duration", store=True)
    phase = fields.Selection(related="name.phase", store=True)
    company_id = fields.Many2one(related="name.company_id", string="Company", store=True)
    vendor = fields.Many2one("res.partner", string="Contractor", domain="[('company_id', '=', False)]")
    start_date = fields.Datetime(string="Start Date", readonly=False, default = datetime.now())
    order_date = fields.Datetime(string="Order Date", readonly=False)
    # solicited_end_date = fields.Datetime(string="Solicited End Date", readonly=False)
    end_date = fields.Datetime(string="End Date", readonly=False)
    time_spent = fields.Integer(compute="_end_start", string="Days spent in activity", readonly=True, store=True)
    time_difference = fields.Integer(compute="_duration_time_spent", string="Days of difference", readonly=True, store=True)
    active = fields.Boolean(default=True)
    pct_completed = fields.Float(string="% Completed")
    completed = fields.Boolean(string="Completed", readonly=True)
    to_approve = fields.Boolean(string="To Approve", readonly=True)
    to_approve_dispute = fields.Boolean(string="To Approve Dispute", readonly=True)
    disputed = fields.Boolean(string="Disputed", readonly=True)
    custodial_money = fields.Boolean(related="project_property.custodial_money", string="Custodial Money", readonly=True)
    superintendent = fields.Many2one(related="project_property.superintendent", string="Superintendent", readonly=True, store=True)
    zone_coordinator = fields.Many2one(related="project_property.zone_coordinator", string="Zone Coordinator", readonly=True, store=True)
    comments = fields.Char(string="Comments")
    act_work_order = fields.Char(compute="_compute_act_name", string="Work Order", readonly=True 
                    #required=True, 
                )
    #Accounting
    invoiced = fields.Boolean(string="Invoiced", default=False)
    invoice_counter = fields.Integer(string="Invoice Counter", default=0, readonly=True)
    invoice_id = fields.Integer(string="Invoice ID", readonly=True)
    expected_end_date = fields.Datetime(string="Expected End Date", readonly=False)

    invoice_ids = fields.One2many(
        "account.move", 
        "linked_activities", 
        string="Invoices",
        help="Invoices linked to this activity."
    )    
    invoice_payment_state = fields.Selection(
        [
            ('not_paid', 'Not Paid'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('partial', 'Partial'),
            ('reversed', 'Reversed'),
            ('invoicing_legacy', 'Invoicing Legacy'),
        ],
        string="Invoice Payment State",
        compute='_compute_invoice_payment_state',
        store=True, 
        readonly=True 
    )

    @api.depends('invoice_ids.payment_state')
    def _compute_invoice_payment_state(self):
        for record in self:
            if record.invoice_ids:
                record.invoice_payment_state = self.env["account.move"].browse(record.invoice_ids.ids[0]).payment_state
            else:
                record.invoice_payment_state = False



    def open_action(self):
        action_view = self.env.ref('pms.pms_projects_view_form')
        return {
            'name': 'Project Activity Form',
            'type': 'ir.actions.act_window',
            'res_model': 'pms.projects.routes',
            'view_mode': 'form',
            'view_id': action_view.id,
            'res_id': self.id,
            'target': 'current',
        }

    def _default_project_property(self):
        last_project = self.env['pms.projects.routes'].search([], limit=1, order='create_date DESC')
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        if last_project and last_project.create_date >= five_minutes_ago:
            self.project_property = last_project.project_property.id
            self._onchange_project_property()
            return last_project.project_property.id
        else:
            return False 

    @api.constrains('project_property')
    def _warning_in_coc(self):
        _logger.info("_warning_in_coc is running...")
        if self.project_property.status_construction in ["coc", "completed"]:
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
            'type': 'danger',
            'title': _("Warning"),
            'message': ('This property is in status COC please check')
        })

    @api.constrains('name', 'project_property')
    def _check_critical_activity_completion(self):
        for record in self:
            new_template_line = record.name

            template_id = new_template_line.route_header.id
            new_sequence = new_template_line.sequence

            property_type = self.project_property.address.own_third

            if property_type == 'own':
                alert_lines = self.env['pms.projects.routes.templates.lines'].search([
                    ('sequence', '<', new_sequence), 
                    ('alert', '=', True),
                    ('route_header', '=', template_id),
                    ('alert_type', '=', 'own')
                ])

                if not alert_lines:
                    alert_lines = self.env['pms.projects.routes.templates.lines'].search([
                    ('sequence', '<', new_sequence), 
                    ('alert', '=', True),
                    ('route_header', '=', template_id),
                    ('alert_type', '=', 'both')
                ])
                    
                if not alert_lines:
                    alert_lines = self.env['pms.projects.routes.templates.lines'].search([
                    ('sequence', '<', new_sequence), 
                    ('alert', '=', True),
                    ('route_header', '=', template_id),
                    ('alert_type', '=', None)
                ])
                    
            elif property_type == 'third':
                alert_lines = self.env['pms.projects.routes.templates.lines'].search([
                    ('sequence', '<', new_sequence), 
                    ('alert', '=', True),
                    ('route_header', '=', template_id),
                    ('alert_type', '=', 'third')
                ])

                if not alert_lines:
                    alert_lines = self.env['pms.projects.routes.templates.lines'].search([
                    ('sequence', '<', new_sequence), 
                    ('alert', '=', True),
                    ('route_header', '=', template_id),
                    ('alert_type', '=', 'both')
                ])
                    
                if not alert_lines:
                    alert_lines = self.env['pms.projects.routes.templates.lines'].search([
                    ('sequence', '<', new_sequence), 
                    ('alert', '=', True),
                    ('route_header', '=', template_id),
                    ('alert_type', '=', None)
                ])

            existing_activities = record.project_property.project_routes_lines.name.mapped('id')

            incomplete_alerts = alert_lines.filtered(lambda line: line.id not in existing_activities)
            if incomplete_alerts:
                raise ValidationError(f"You cannot create this activity without first completing the critical activity: {', '.join(incomplete_alerts.mapped('name'))}.")

    # exclude_from_processing = fields.Boolean(
    #     string="Exclude Activity",
    #     default=False,
    #     help="If checked, this activity will be excluded from on hold check."
    # )

    @api.constrains('project_property')
    def _check_project_on_hold(self):
        
        excluded_activities = [
            '4th Construction Fee',
            'Request Co',      
        ]
        excluded_activities_lower = [p.lower() for p in excluded_activities]
        
        for record in self:
            is_name_excluded = False
            # Check if record.name exists before trying to convert to lower or check substring
            if record.name:
                record_name_lower = record.name.name.lower()
                for activity_lower in excluded_activities_lower:
                    if activity_lower in record_name_lower:
                        is_name_excluded = True
                        break

            if not is_name_excluded and record.project_property and record.project_property.on_off_hold:
                raise ValidationError("The selected project is on hold. You cannot create an activity for this project.")


    # def create_invoice_wizard(self):
    #     ctx = dict(
    #         active_ids=self.ids
    #         )
        
    #     invoice_wizard_form = self.env.ref('pms.view_invoice_wizard_form')
    #     return {
    #             'name': 'Invoice Wizard',
    #             'type': 'ir.actions.act_window',
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': 'invoice.wizard',
    #             'views': [(invoice_wizard_form.id, 'form')],
    #             'view_id': invoice_wizard_form.id,
    #             'target': 'new',
    #             'context': ctx}
    
    def view_invoice(self):
        if self.invoice_id == False:
            raise UserError(_('No Invoice found'))
        else:
            return {
            'type': 'ir.actions.act_window',
            'name': ('account.view_move_form'),
            'res_model': 'account.move',
            'res_id': self.invoice_id,
            'view_mode': 'form'}
    
    @api.depends("project_property.address.on_hold")
    def _compute_on_hold(self):
        for record in self:
            if record.project_property.address.on_hold == True:
                record.on_hold = True
            else:
                record.on_hold = False

    @api.depends("name", "county")
    def _compute_act_name(self):
        for record in self:
            if record.name and record.county:
                record.act_work_order = f"{record.name.acronym}{record.county.name[:2]}#{record.id}"
            else:
                record.act_work_order = " "

    def new_bulk_activities(self):
        new_bulk_form = self.env.ref('pms.view_new_bulk_wizard_form')
        return {
                'name': 'New Bulk Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'new.bulk.wizard',
                'views': [(new_bulk_form.id, 'form')],
                'view_id': new_bulk_form.id,
                'target': 'new'}

    @api.onchange("project_property")
    def _onchange_project_property(self):
        for record in self:
            if record.project_property:
                record.project_routes = record.project_property.project_routes.id
                # Change the activity name to the following activity in the route
                phase_activities = record.env["pms.projects.routes.templates.lines"].search(["&", ("route_header", "=", record.project_property.project_routes.id), ("phase", "=", record.project_property.status_construction)])
                if phase_activities:
                    activities = phase_activities.filtered(lambda x: x.id not in record.project_property.project_routes_lines.name.mapped("id"))
                    if activities:
                        record.name = activities.sorted(key=lambda x: x.sequence)[0].id 
            else:
                record.project_routes = 0  # Use 0 instead of False/None for integer field

    # Make onchange function to change vendor field based on the name field
    @api.onchange("name")
    def _onchange_name(self):
        for record in self:
            if record.name:
                record.vendor = record.name.vendor.id
            else:
                record.vendor = False

    def print_activities_report(self):
        return self.env.ref('pms.report_draws_pms_action').report_action(self)

    def order_jobs(self): # optimized for one single write
        for record in self:
            vals = {}
            if not record.order_date:
                vals['order_date'] = datetime.now()
            if record.name.phase in ["cop", "cop1", "cop2", "cop3", "cop4", "coc", "completed"]:
                record.project_property.from_activity = True # shouldnt cause two writes since its on another model (related field)
            if vals:
                record.write(vals)
                record._calculate_cons_status()

    # def ask_approval(self):
    #     jobs_info = []
    #     for record in self:
    #         if record.start_date == False: 
    #             record.start_date = datetime.now()
    #             record.pct_completed = 1.00
    #             record.completed = True
    #             today = datetime.now()
    #             record.end_date = today
    #             # record.project_property._calculate_construction_status()
    #             record._calculate_cons_status()
                
    #         else:
    #             record.completed = True
    #         # end date for activity
    #             today = datetime.now()
    #             record.end_date = today 
    #         # mark as delivered in purchase orders
    #             # record._marked_po_receipted()
    #             # record.project_property._calculate_construction_status()
    #             record._calculate_cons_status()
                
    #         record.to_approve = True

    # def approve_completion(self):
    #     if self.env.user.has_group("pms.approver"):
    #         for record in self:
    #             record.to_approve = False 
            
    # def approve_dispute_job(self):
    #     if self.env.user.has_group("pms.approver"):
    #         for record in self:
    #             record.to_approve_dispute = False
    #             record.disputed = True

    # def dispute_job(self):
    #     jobs_info = []
    #     for record in self:
    #         record.to_approve_dispute = True

    def _calculate_cons_status(self):
        for record in self:
            if record.sequence > record.project_property.max_sequence:
                record.project_property.max_sequence = record.sequence
                record.project_property.status_construction = record.phase


    # def _complete_jobs(self):
    #     for record in self:
    #         record.to_approve = False 
    #         record.pct_completed = 1.00
    #         record.completed = True
    #         today = datetime.now()
    #         record.end_date = today
    #         # record._marked_po_receipted()
    #         if record.start_date == False: 
    #             record.start_date = datetime.now()
    #         record._calculate_cons_status()
    def _complete_jobs(self): # optimized for one single write
        for record in self:
            vals = {
                'to_approve': False,
                'pct_completed': 1.00,
                'completed': True,
                'end_date': datetime.now(),
            }

            if not record.start_date:
                vals['start_date'] = datetime.now()

            record.write(vals)
            record._calculate_cons_status()



    def uncomplete_jobs(self): # optimized for one single write
        for record in self:
            vals = {
                'pct_completed': 0.00,
                'completed': False,
                'end_date': '',
            }
            record.write(vals)
            
        # mark jobs as completed
            # record.pct_completed = 0
            # record.completed = False
            # record.end_date = ''
            # record.project_property._calculate_construction_status()
            # record._marked_po_unreceipted()
           

            
    @api.depends("start_date", "end_date", "time_spent", "order_date")       
    def _end_start(self):
        for record in self:
            if record.order_date and record.end_date and record.start_date:
                record.time_spent = (record.end_date.date() - record.order_date.date()).days
            elif record.order_date and not record.end_date: 
                record.time_spent = (datetime.today().date() - record.order_date.date()).days
            # elif record.start_date and record.end_date and not record.order_date: 
            #     record.time_spent = (record.end_date - record.start_date).days #     if record.time_spent < 0:
            #         record.time_spent = 0

            # elif record.start_date and not record.end_date and not record.order_date:
            #     record.time_spent = (datetime.now() - record.start_date).days
            #     if record.time_spent < 0:
            #         record.time_spent = 0



    @api.depends("duration", "time_spent")
    def _duration_time_spent(self):
        for record in self:
            record.time_difference = record.duration - record.time_spent
            


    def _marked_po_receipted(self):
        # mark purchase orders linked to the activity as receipted
        for record in self:
            if record.pos:
                for po in record.pos:
                    #call stock module function to mark as receipted
                    po.order_id.picking_ids.move_ids._set_quantities_to_reservation()
                    po.order_id.picking_ids._action_done()
            else:
                pass

    #function that marks po as unreceipted
    def _marked_po_unreceipted(self):
        for record in self:
            if record.pos:
                for po in record.pos:
                    #call stock module function to mark as unreceipted
                    po.order_id.picking_ids.move_ids._set_quantities_to_reservation()
                    po.order_id.picking_ids._action_cancel()
            else:
                pass
     
    def open_job_wizard(self):
        ctx = dict(
            active_ids=self.ids
            )
        
        order_jobsform = self.env.ref('pms.view_pms_orderjobs_wizard_form')
        return {
                'name': 'Order Jobs Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'pms.orderjobs.wizard',
                'views': [(order_jobsform.id, 'form')],
                'view_id': order_jobsform.id,
                'target': 'new',
                'context': ctx}


    @api.constrains('name')
    def check_job(self):
        for record in self:
            if record.name:
                check = record.search(["&", ("name.id", "=", record.name.id), "&", ("project_property", "=", record.project_property.id), ("id", "!=", record.id)])
                if check:
                    raise ValidationError("This job has already been created for this project. Please check again or contact Diego")
                else:
                    pass
            else:
                pass

    def _send_weekly_report_activities(self):

        end_of_day = datetime.combine(datetime.now(), time.max)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=7)

        records = self.search([ ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])

        lista_county = set(records.mapped("county"))

        for x in lista_county:

            county_filter = records.filtered(lambda r: r.county == x)
            
            data_record = base64.b64encode(self.env.ref("pms.report_project_activities_pms_action").sudo()._render_qweb_pdf(self.env.ref("pms.report_project_activities_pms_action").ids[0], county_filter.ids)[0])        
            ir_values = {
                'name': f"{x.name}WeeklyActivitiesReport{date.today()}.pdf",
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record
                }
            data_id = self.env['ir.attachment'].create(ir_values)
            
            email_template = self.env.ref('pms.email_template_activities_report')
            i = 0
            for record in self:
                if i < 1:
                    email_template.attachment_ids = [(4, data_id.id)]
                    email_value={'subject': f'{x.name} Weekly Activities Report'}
                    email_template.send_mail(record.id, email_values = email_value, force_send=True)
                    email_template.attachment_ids = [(5, 0, 0)]

                    i = i + 1
                else:
                    pass

    def _send_daily_report_activities(self):

        end_of_day = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=1)

        records = self.search([ ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])

        lista_county = set(records.mapped("county"))

        for x in lista_county:

            county_filter = records.filtered(lambda r: r.county == x)
            
            data_record = base64.b64encode(self.env.ref("pms.report_project_activities_pms_action").sudo()._render_qweb_pdf(self.env.ref("pms.report_project_activities_pms_action").ids[0], county_filter.ids)[0])        
            ir_values = {
                'name': f"{x.name}DailyActivitiesReport{date.today()}.pdf",
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record
                }
            data_id = self.env['ir.attachment'].create(ir_values)
            
            email_template = self.env.ref('pms.email_template_activities_report_daily')
            i = 0
            for record in self:
                if i < 1:
                    email_template.attachment_ids = [(4, data_id.id)]
                    email_value={'subject': f'{x.name} Daily Activities Report'}
                    email_template.send_mail(record.id, email_values = email_value, force_send=True)
                    email_template.attachment_ids = [(5, 0, 0)]

                    i = i + 1
                else:
                    pass

                
    def activity_check(self):
        _logger.info("Entering activity_check")
        
        for record in self:
            
            project = record.project_property
            activity_name = record.name.name
            
            if not project:
                _logger.warning("No project_property found for activity record ID: %s. Skipping.", record.id)
                continue
            if not activity_name:
                _logger.warning("Activity record ID: %s has no activity name. Skipping.", record.id)
                continue
            
            is_lot_clearing = 'lot clearing' in activity_name.lower()
            is_request_co = 'request co' in activity_name.lower()
            is_septic_permit_issued = 'septic permit issued' in activity_name.lower()


            # Project Duration checks
            
            if is_lot_clearing:
                _logger.info("Lot Clearing template found")
                if record.order_date and not (record.order_date == project.start_project):
                    project.start_project = record.order_date
                elif not record.order_date:
                    project.start_project = False
                else: continue
            if is_request_co:
                _logger.info("Request CO template found")
                if record.order_date and not (record.order_date == project.end_project):
                    project.end_project = record.order_date
                elif not record.order_date:
                    project.end_project = False
                else: continue
                
            # Septic Permit Issued check
                
            if is_septic_permit_issued:
                _logger.info("Septic Permit Issued template found")
                if record.order_date and not (record.order_date == project.septic_permit_issued):
                    project.septic_permit_issued = record.order_date
                if record.order_date and (record.end_date or record.completed):
                    project.septic_permit_completed = True
                elif not record.order_date:
                    project.septic_permit_issued = False
                    project.septic_permit_completed = False
            
            if not is_lot_clearing and not is_request_co and not is_septic_permit_issued:
                _logger.warning("Neither 'Lot Clearing', 'Request CO' nor 'Septic Permit Issued' activity found. Skipping.")
                continue


    @api.model
    def create(self, vals):
        _logger.info("Activity create method called with vals: %s", vals)
        record = super(pms_projects_routes, self).create(vals)
        _logger.info("New activity record created with ID: %s", record.id)
        record.activity_check()
        return record

    def write(self, vals):
        _logger.info("Activity write method called for records: %s with vals: %s", self.ids, vals)
        res = super(pms_projects_routes, self).write(vals)
        self.activity_check()
        return res


    # def send_activity_update_email(self, record):

    #     email_addresses = ["adan@adanordonezp.com"]
    #     if record.vendor.email and record.vendor.email not in email_addresses:
    #         email_addresses.append(record.vendor.email)
    #     email_to = ','.join(email_addresses)

    #     mail_values = {
    #         'subject': f'Project Activity Updated: {record.name.name}',
    #         'body_html': f"""
    #         <html>
    #             <head>
    #                 <meta charset="UTF-8">
    #                 <title>Project Activity Updated</title>
    #             </head>
    #             <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f8f8; padding: 20px; margin: 0;">
    #                 <div style="background-color: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); max-width: 600px; margin: 20px auto;">
    #                     <h1 style="color: #007bff; font-size: 28px; margin-bottom: 20px; text-align: center;">Project Activity Updated</h1>
    #                     <p style="margin-bottom: 20px;">The following project activity has been updated:</p>

    #                     <div style="background-color: #f0f8ff; padding: 20px; border-radius: 5px; margin-bottom: 20px;">
    #                         <h2 style="color: #333; margin-bottom: 15px;">Activity Details</h2>
    #                         <p><strong>Project Property:</strong> <span style="color: #28a745;">{record.project_property.name}</span></p>
    #                         <p><strong>Activity Name:</strong> <span style="color: #28a745;">{record.name.name}</span></p>
    #                         <p><strong>Percentage Completed:</strong> {record.pct_completed}%</p>
    #                         <p><strong>Vendor:</strong> {record.vendor.name if record.vendor else 'Not Assigned'}</p>
    #                         <p><strong>Comments:</strong> {record.comments if record.comments else 'None'}</p>
    #                     </div>

    #                     <p style="font-size: 14px; color: #777;">This email was automatically generated by the system.</p>
    #                 </div>
    #             </body>
    #         </html>
    #     """,
    #         'email_to': email_to,
    #     }
    #     self.env['mail.mail'].sudo().create(mail_values).send()
    
