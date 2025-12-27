from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date

import logging
_logger = logging.getLogger(__name__)

class pms_projects(models.Model):
    _name = "pms.projects"
    _description = "Table for Property Project Management"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Project Name", index=True, compute="_calculate_project_name", store=True)
    address = fields.Many2one("pms.property", string="Property Address")
    county = fields.Many2one("pms.county", related="address.county", readonly=True, store=True)
    house_model = fields.Many2one("pms.housemodels", related="address.house_model", store=True)
    parcel_id = fields.Char(related="address.parcel_id", readonly=True)
    owner_property = fields.Many2one(related="address.partner_id", readonly=True, string="Owner", store=True)
    project_manager = fields.Many2one("hr.employee", string="Project Manager")
    superintendent = fields.Many2one("hr.employee", string="Superintendent")
    zone_coordinator = fields.Many2one("hr.employee", string="Zone Coordinator")
    status_construction = fields.Selection(selection=[
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
        ], string="Construction Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='pending')
    on_off_hold = fields.Boolean(related="address.on_hold", string= "On Hold", readonly=False, tracking=True)
    project_routes = fields.Many2one("pms.projects.routes.templates", string="Project Route")
    project_routes_lines = fields.One2many("pms.projects.routes", "project_property", string="Project Routes Lines", readonly=True)
    next_activity = fields.Many2one("pms.projects.routes", compute="_next_jobsheader", string="Next Activity", readonly=True, store=True)
    next_orderdate = fields.Datetime(compute="_next_jobsheader",string="Next Activity Date", readonly=True, store=True)
    next_vendor = fields.Char(compute="_next_jobsheader",string="Next Activity Vendor", readonly=True, store=True)
    project_completed = fields.Boolean(compute="_completed_activities", string="Completed", store=True)
    visit_day = fields.Selection(selection=[("monday", "Monday"),("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday")], string="Visit Day", tracking=True)
    second_visit_day = fields.Selection(selection=[("monday", "Monday"), ("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday")], string="Second Visit Day", tracking=True)
    start_project = fields.Datetime(string="Start Date", readonly=False)
    end_project = fields.Datetime(string="End Date", readonly=False)
    project_duration = fields.Integer(compute="_calculate_project_duration", string="Project Duration", store=True)
    active = fields.Boolean(default=True)
    custodial_money = fields.Boolean(string="Custodial Money")
    escrow_company = fields.Many2one("res.company", string="Escrow Company")
    comments = fields.Char(string="Comments")
    own_third_property = fields.Selection(related="address.own_third", readonly=True, string="Own/Third", store=True)
    last_updated_on = fields.Datetime(string="Last Updated On", compute="_calculate_last_update", store=True)
    visit_days = fields.One2many("pms.visit.days", "property_project", string="Visit Days", readonly=True)
    last_visit_day = fields.Date(string="Last Visit Day", compute="_compute_last_visit_day", store=True)
    days_since_last_visit = fields.Integer(string="Days Since Last Visit", compute="_compute_days_since_last_visit", store=True)
    construction_started = fields.Boolean(string="Construction Started", compute="_compute_construction_started", default=False, readonly=True)
    from_activity = fields.Boolean(string="From Activity", default=False)
    stand_by = fields.Boolean(string="Stand By")
    lot_clear = fields.Boolean(string="Lot Clear")
    starting_activity = fields.Many2one("pms.projects.routes.templates.lines", string="Starting Activity")
    loan_expiration = fields.Date(compute="_compute_loan_expiration", readonly=True, store=True)
    expected_co_date = fields.Date(string="Expected CO Date", store=True, compute='_compute_expected_co_date')
    issued_date = fields.Date(string="Issued Date", tracking=True)
    expiration_date = fields.Date(string="Expiration Date", tracking=True)
    available_for_rent = fields.Boolean(related="address.available_for_rent", string="Available for Rent")
    available_for_sale = fields.Boolean(related="address.available",string="Available for Sale")
    
    max_sequence = fields.Integer(string="Max Sequence", store=True)
    
    notified_cop4 = fields.Boolean(string="Notified COP4", default=False, store=True)
    
    auto_lines = fields.Boolean(string="Lines Automatically Created", default=False, readonly=True)
    
    septic_permit_issued = fields.Datetime(string="Septic Permit Issued", help="Date when the septic permit was issued for the project.")
    septic_permit_completed = fields.Boolean(string="Septic Permit Completed", help="Indicates whether the septic permit process has been completed for the project.")
    septic_permit_warning_state = fields.Char(
        string="Septic Permit Warning",
        compute='_compute_septic_permit_warning_state',
        store=False
    )
    
    # Schedule Tracking Fields
    schedule_start_date = fields.Date(# Consultar si compute o manual
        string="Schedule Start Date",
        compute="_compute_schedule_start_date",
        store=True,
        help="The scheduled start date of the project"
    )
    schedule_end_date = fields.Date(
        string="Schedule End Date",
        compute="_compute_schedule_end_date",
        store=True,
        help="The scheduled end date of the project"
    )
    days_on_pause = fields.Integer(
        string="Days on Pause",
        store=True,
        help="Total days the project has been on hold"
    )
    delayed_invoice_payments = fields.Integer( # Días with delay
        string="Delayed Invoice Payments",
        store=True,
        help="Number of invoices with delayed payments"
    )
    on_time_invoice_payments = fields.Integer( # Preguntar si lo quieren
        string="On Time Invoice Payments",
        store=False,
        help="Number of invoices paid on time"
    )
    delayed_invoice_list = fields.Many2many(
        'account.move',
        'pms_projects_delayed_invoice_rel',
        'project_id',
        'invoice_id',
        string="Delayed Invoice Payments",
        store=True,
        help="List of invoices with 3+ days of delay"
    )
    on_time_invoice_list = fields.Many2many(
        'account.move',
        'pms_projects_on_time_invoice_rel',
        'project_id',
        'invoice_id',
        string="On Time Invoice Payments",
        store=True,
        help="List of invoices with less than 3 days delay"
    )
    total_effective_time = fields.Integer(
        string="Total Effective Time (Days)",
        compute="_compute_total_effective_time",
        store=True,
        help="Total project duration minus days on pause"
    )
    total_late_days = fields.Integer(
        string="Total Late Days",
        store=True,
        help="Total number of days overdue across all late invoices"
    )
    
    # Display fields with "days" suffix
    project_duration_display = fields.Char(
        string="Project Duration",
        compute="_compute_project_duration_display",
        store=False,
        help="Project duration with 'days' suffix"
    )
    days_on_pause_display = fields.Char(
        string="Days on Pause",
        store=False,
        help="Days on pause with 'days' suffix"
    )
    total_effective_time_display = fields.Char(
        string="Total Effective Time",
        store=False,
        help="Total effective time with 'days' suffix"
    )

    @api.depends('septic_permit_issued', 'septic_permit_completed')
    def _compute_septic_permit_warning_state(self):
        today = date.today() 
        
        for record in self:
            record.septic_permit_warning_state = False

            if not record.septic_permit_completed and record.septic_permit_issued:
                issued_date_only = record.septic_permit_issued.date()
                
                days_since_issued = (today - issued_date_only).days

                _logger.debug("Septic Permit Issued (Date Only): %s, Today: %s, Days Since Issued: %s",
                              issued_date_only, today, days_since_issued)

                if days_since_issued >= 15:
                    record.septic_permit_warning_state = 'severe_warning'
                elif days_since_issued >= 7:
                    record.septic_permit_warning_state = 'warning'
                    
    def action_create_project_activities(self):
        self.ensure_one()

        if not self.project_routes:
            raise UserError(_("Please select a Project Route Template first."))

        # if self.project_routes_lines:
        #     raise UserError(_("Project activities already exist for this project. Delete existing activities or adjust the template if you wish to regenerate."))

        existing_activity_template_line_ids = self.project_routes_lines.mapped('name').ids

        activities_to_create = []
        active_template_lines = self.project_routes.route_lines.filtered(lambda line: line.active)

        for line in active_template_lines:
            if line.id in existing_activity_template_line_ids: continue # Skip this line if it exists
                
            activity_vals = {
                'project_property': self.id,
                'name': line.id,
                'product': line.product.id,
                'activity_type': line.activity_type,
                'sequence': line.sequence,
                'duration': line.duration,
                'phase': line.phase,
                'company_id': line.company_id.id,
                'vendor': line.vendor.id,
                'project_routes': self.project_routes.id,
            }
            activities_to_create.append(activity_vals)

        if activities_to_create:
            self.env['pms.projects.routes'].create(activities_to_create)
            self.auto_lines = True
            self.message_post(body=_("Project activities generated successfully from route template '%s'.") % self.project_routes.name)
        else:
            raise UserError(_("No activities found in the selected Project Route Template."))
        
    def action_clear_project_activities(self):
        self.ensure_one() # Ensure the method is called on a single project record

        if not self.project_routes_lines:
            raise UserError(_("There are no project activities to clear for this project."))

        # Delete all associated project_routes_lines
        self.project_routes_lines.unlink()
        self.auto_lines = False
        self.message_post(body=_("All project activities for this project have been cleared."))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload', # Reload the view to reflect the changes immediately
        }
    # call_day = fields.Selection( string="Visit Day", selection=[
    #     ("monday", "Monday"), ("tuesday", "Tuesday"), ("wednesday", "Wednesday"), 
    #     ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday"), 
    #     ("sunday", "Sunday"), ("any", "Any")], default="any"
    # )
    # owner_call_day = fields.Char("Owner Call Day", compute="_get_owner_call_day", store=True)

    # # GET OWNER CALL DAY
    # @api.depends('owner_property')
    # def _get_owner_call_day(self):
    #     for record in self:
    #         owner = self.env["res.partner"].search([
    #             ('owner_property', '=', record.partner_id.id)
    #         ])
    #         record.owner_call_day = owner.call_day


    def function_run_log(self, function_name):
        _logger.info("DEBUGGING: The following function is running: %s", function_name)
        
    def _update_invoices_custodial_money(self):
        analytic_account_id = self.address.analytical_account.id

        account_move_lines = self.env['account.move.line'].search([('analytic_distribution', '=', {str(analytic_account_id): 100.0})])

        for line in account_move_lines:
            account_move = line.move_id
            company = self.env['res.company'].search([('partner_id', '=', self.address.partner_id.id)])

            analytic_distributions = account_move.invoice_line_ids.mapped('analytic_distribution')

            valid_analytic_distributions = [
                dist for dist in analytic_distributions 
                if dist and any(key for key, value in dist.items() if value > 0)
            ]

            if len(valid_analytic_distributions) > 1:
                account_move.write({'invoice_type': 'various'})
                continue

            if self.custodial_money and not self.on_off_hold:
                account_move.write({'invoice_type': 'escrow'})
            elif self.custodial_money and self.on_off_hold:
                account_move.write({'invoice_type': 'hold'})
            elif not self.custodial_money:
                if self.on_off_hold:
                    account_move.write({'invoice_type': 'hold'})
                elif company:
                    account_move.write({'invoice_type': '1stparty'})
                else:
                    account_move.write({'invoice_type': '3rdparty'})


    def _compute_loan_expiration(self):
        for record in self:
            search_loan = record.env["pms.loans"].search(['&', ("property_address", "=", record.address.id), ("exit_status", "=", "ongoing")], limit=1)
            if search_loan:
                record.loan_expiration = search_loan.maturity_date
            else:
                record.loan_expiration = False

    def set_available(self):
        self.address.available = True

    def set_unavailable(self):
        self.address.available = False

    def set_available_for_rent(self):
        self.address.available_for_rent = True

    def set_unavailable_for_rent(self):
        self.address.available_for_rent = False

    # @api.onchange("status_construction")
    # def property_coc(self):
    #     if self.status_construction == "coc" or self.status_construction == "completed":
    #         property_construction = self.env["pms.property"].search(['&',("id", "=", self.address.id),("status_property", "=", "construction")])
    #         if property_construction:
    #             property_construction.to_coc()
    #         else:
    #             pass
    
    
    @api.onchange('status_construction')
    def notify_on_status_cop4(self):
        for record in self:
            if record.status_construction == "cop4" and not record.notified_cop4:
                record.notified_cop4 = True
                emails = [
                    "oswaldo@adanordonezp.com"
                ]
                email_to = ','.join(emails)
                
                mail_values = {
                        'subject': f'Project: {self.name} has reached COP4',
                        'body_html': f"""
                            <html>
                                <head>
                                <meta charset="UTF-8">
                                    <title>Project Construction Status is now COP4</title>
                                </head>
                                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f8f8; padding: 20px; margin: 0;">
                                    <div style="background-color: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); max-width: 600px; margin: 20px auto;">
                                        <h1 style="color: #007bff; font-size: 28px; margin-bottom: 20px; text-align: center;">Project Construction Status is now COP4</h1>
                                        <p style="margin-bottom: 15px;">The following project has reached COP4:</p>
                                        <p><span style="font-weight: bold; color: #28a745;">{self.name}</span></p>
                                    </div>
                                </body>
                            </html>
                        """,
                        'email_to': email_to
                    }
                self.env['mail.mail'].sudo().create(mail_values).send()
            else:
                return
    
    # implement rent / sold check so it doenst update??
    def property_coc(self):
        for record in self:
            if record.address:
                property = self.env["pms.property"].browse(record.address.id)
                if property:
                    if property.status_property == "rented":
                        return
                    if record.status_construction in ("coc", "completed"):
                        property.status_property = "coc"

    @api.depends('status_construction')
    def _compute_construction_started(self):
        for record in self:
            if record.status_construction in ["cop1", "cop2", "cop3", "cop4", "cop5", "coc", "completed"]:    
                record.construction_started = True
            elif record.status_construction == "cop" and record.from_activity == False:
                    record.construction_started = False
            elif record.status_construction == "cop" and record.from_activity == True:
                record.construction_started = True
            else:
                record.construction_started = False

    def update_status_construction(self, new_status):
        if new_status in ["cop1", "cop2", "cop3", "cop4", "cop5", "coc", "completed"]:
            self.write({'status_construction': new_status, 'construction_started': True})
        elif new_status == "cop":
            if not self.env.context.get('from_activity', False):
                self.write({'status_construction': new_status, 'construction_started': False})
        else:
            self.write({'status_construction': new_status, 'construction_started': False})

    @api.depends('address')
    def _compute_last_visit_day(self):
        for project in self:
            visit_record = self.env['pms.visit.days'].search([
                ('property_name', '=', project.address.id)
            ], order='visit_date desc', limit=1)
            project.last_visit_day = visit_record.visit_date if visit_record else False
            
    def _update_days_since_last_visit(self):
        for project in self:
            project._compute_days_since_last_visit()

    @api.depends('last_visit_day')
    def _compute_days_since_last_visit(self):
        for project in self:
            if project.last_visit_day:
                project.days_since_last_visit = (fields.Date.today() - project.last_visit_day).days
                if project.days_since_last_visit < 0:
                    project.days_since_last_visit = 0
            else:
                project.days_since_last_visit = 0   

    # Potential new function more optimized
    # @api.depends('last_visit_day')
    # def _compute_days_since_last_visit(self):
    #     for project in self:
    #         if project.last_visit_day:
    #             project.days_since_last_visit = max((fields.Date.today() - project.last_visit_day).days, 0)
    #         else:
    #             project.days_since_last_visit = 0

    @api.depends("address", "parcel_id")
    def _calculate_project_name(self):
        if self.address and self.parcel_id:
            self.name = f"Construction {self.address.name} {self.parcel_id}"
        else:
            self.name = " "

    def on_hold_button(self):
        self.address.on_hold = True

    def off_hold_button(self):
        self.address.on_hold = False

    # Ponerlo en un scheduled action una vez y ya
    def _calculate_construction_status(self):
        for record in self:
            if record.project_routes_lines:
                set_of_activities = record.project_routes_lines.filtered(lambda x: x.completed == True) # or x.order_date != False
                if set_of_activities:
                    max_sequence = max(set_of_activities.mapped("sequence"))
                    new_status = set_of_activities.filtered(lambda x: x.sequence == max_sequence).mapped("phase")[0]
                    record.status_construction = new_status
                    record.max_sequence = max_sequence
                else:
                    record.status_construction = "epp"

            else:
                record.status_construction = "epp"
    
    estimated_cop2 = fields.Date(string="Estimated COP2 Date", compute="_compute_cop_to_cop2", store=True)

    @api.depends('project_routes_lines.order_date', 'project_routes_lines.name', 'project_routes_lines.sequence')
    def _compute_cop_to_cop2(self):
        for record in self:
            _logger.info(f"Processing record: {record.id} for estimated_cop2")
            record.estimated_cop2 = False
            if record.project_routes_lines:
                lot_clearing_lines = record.project_routes_lines.filtered(lambda x: "Lot Clearing" in x.name.name and x.order_date)
                if lot_clearing_lines:
                    lot_clearing_date = lot_clearing_lines[0].order_date.date()
                    _logger.info(f"Lot Clearing Date: {lot_clearing_date}")
                    working_days_count = 0
                    current_date = lot_clearing_date
                    while working_days_count < 45:
                        current_date += timedelta(days=1)
                        if current_date.weekday() != 6:
                            working_days_count += 1
                    record.estimated_cop2 = current_date
                    _logger.info(f"Estimated COP2 Date: {current_date}")
                else:
                    _logger.info(f"No 'Lot Clearing' line found with order date for record {record.id}")
            else:
                 _logger.info(f"No project route lines found for record {record.id}")


    # def _calculate_construction_status(self): # Updated construction_status function to take phase from the last completed activity with greatest sequence 
    #     for record in self:
    #         if record.project_routes_lines:
    #             completed_activities = record.project_routes_lines.filtered(lambda x: (x.completed == True or x.order_date != False) and x.sequence != 0)
    #             if completed_activities:
    #                 if record.max_sequence:
    #                     filtered_activities = completed_activities.filtered(lambda x: x.sequence >= record.max_sequence)
    #                 else:
    #                     filtered_activities = completed_activities

    #                 if filtered_activities:
    #                     max_sequence = max(filtered_activities.mapped("sequence"))
    #                     new_status = filtered_activities.filtered(lambda x: x.sequence == max_sequence).mapped("phase")[0]
    #                     record.status_construction = new_status
    #                     record.max_sequence = max_sequence
    #                 else:
    #                     pass
    #             else:
    #                 record.status_construction = "epp"
    #                 record.max_sequence = 0
    #         else:
    #             record.status_construction = "epp"
    #             record.max_sequence = 0
                
    @api.onchange('max_sequence')
    def _compute_expected_co_date(self):
        _logger.info("Compute Expected CO Date Running...")
        for project in self:
            if project.status_construction in ['cop3', 'cop4', 'cop5']:
                if project.project_routes:
                    query = """
                        SELECT
                            (CURRENT_DATE + INTERVAL '1 day' * COALESCE(SUM(tmpl_line.duration), 0)) AS expected_co_date
                        FROM
                            pms_projects proj
                        JOIN
                            pms_projects_routes_templates route_template ON route_template.id = proj.project_routes
                        JOIN
                            pms_projects_routes_templates_lines tmpl_line ON tmpl_line.route_header = route_template.id
                        LEFT JOIN
                            pms_projects_routes act ON act.project_property = proj.id AND act.name = tmpl_line.id
                        WHERE
                            (act.id IS NULL OR act.completed = FALSE)
                            AND tmpl_line.add_to_report = TRUE
                            AND proj.id = %s
                    """

                    self.env.cr.execute(query, (project.id,))
                    result = self.env.cr.fetchone()
                    if result and result[0]:
                        project.expected_co_date = result[0]
                    else:
                        project.expected_co_date = False
                else:
                    project.expected_co_date = False
            else:
                project.expected_co_date = False
                    # query = """
                    #     SELECT
                    #         (CURRENT_DATE + INTERVAL '1 day' * COALESCE(SUM(tmpl_lines.duration), 0)) AS expected_co_date
                    #     FROM
                    #         pms_projects_routes_templates_lines tmpl_lines
                    #     LEFT JOIN
                    #         pms_projects_routes act ON act.project_property = %s AND act.name = tmpl_lines.id
                    #     LEFT JOIN 
                    #         (
                    #             SELECT 
                    #                 project_property, 
                    #                 MAX(tmpl_line.sequence) AS max_completed_sequence
                    #             FROM 
                    #                 pms_projects_routes act
                    #             JOIN 
                    #                 pms_projects_routes_templates_lines tmpl_line ON act.name = tmpl_line.id
                    #             WHERE 
                    #                 act.completed = TRUE
                    #             GROUP BY 
                    #                 project_property
                    #         ) AS completed_sequences
                    #         ON completed_sequences.project_property = %s
                    #     WHERE
                    #         (act.id IS NULL OR act.completed = FALSE)
                    #         AND tmpl_lines.add_to_report = TRUE
                    # """
                
    # Run this in scheduled action to update expected_co_date
    # model.search([])._compute_expected_co_date()


    @api.depends("project_routes_lines.write_date")
    def _calculate_last_update(self):
        for record in self:
            if record.project_routes_lines:
                last_update = max(record.project_routes_lines.mapped("write_date"))
                record.last_updated_on = last_update
            else:
                record.last_updated_on = False

    @api.onchange('on_off_hold', 'address', "status_construction", "project_manager", "project_routes", "visit_day", "custodial_money", "comments", "project_routes_lines.address")
    def _onchange_update_last_updated_on(self):
        for record in self:
            record.last_updated_on = fields.Datetime.now()

#Funcion que chequea si las ultima actividad fue completada NO COMPLETADA
    @api.depends("project_routes_lines.completed")
    def _completed_activities(self):
        for record in self:
           if record.project_routes and record.project_routes.route_lines:
                max_sequence = max(record.project_routes.route_lines.mapped("sequence"))
                max_activity = record.project_routes_lines.filtered(lambda x: x.sequence == max_sequence and x.completed == True)
                if max_activity:
                    record.project_completed = True
                    record.status_construction = "completed"
                else:
                    record.project_completed = False
        else:
            record.project_completed = False
    
    @api.depends('start_project', 'project_routes_lines.order_date')  # Si lo quieren manual borrar - Performance: Consider scheduled action if compute becomes slow
    def _compute_schedule_start_date(self):
        """Calculate schedule start date from project start or first activity order date"""
        for record in self:
            if record.start_project:
                record.schedule_start_date = record.start_project.date()
            elif record.project_routes_lines:
                first_activity = record.project_routes_lines.filtered(lambda x: x.order_date).sorted('order_date')
                if first_activity:
                    record.schedule_start_date = first_activity[0].order_date.date()
                else:
                    record.schedule_start_date = False
            else:
                record.schedule_start_date = False
    
    @api.depends('end_project', 'project_routes_lines.end_date', 'expected_co_date')
    def _compute_schedule_end_date(self):
        """Calculate schedule end date from project end, last activity end date, or expected CO date"""
        for record in self:
            if record.end_project:
                record.schedule_end_date = record.end_project.date()
            elif record.expected_co_date:
                record.schedule_end_date = record.expected_co_date
            elif record.project_routes_lines:
                last_activity = record.project_routes_lines.filtered(lambda x: x.end_date).sorted('end_date', reverse=True)
                if last_activity:
                    record.schedule_end_date = last_activity[0].end_date.date()
                else:
                    record.schedule_end_date = False
            else:
                record.schedule_end_date = False
    
    def _compute_days_on_pause(self):
        """Calculate total days on pause from on hold history"""
        today = date.today()
        for record in self: 
            if not record.address:
                record.days_on_pause = 0
                continue
            
            # Get all on hold history records for this property, ordered by date
            hold_history = self.env['pms.on.hold.history'].search([
                ('property_name', '=', record.address.id)
            ], order='date asc')
            # revisar order
            total_days = 0
            for hold_record in hold_history: # Review if it takes too long
                if not hold_record.date:
                    continue
                
                hold_start = hold_record.date
                
                # Determine end date
                if hold_record.hold_end_date:
                    # Has explicit end date
                    hold_end = hold_record.hold_end_date.date()
                elif record.address.on_hold:
                    # Property is currently on hold and this is the active hold record
                    # Check if this is the most recent hold record without an end date
                    more_recent_holds = hold_history.filtered(
                        lambda h: h.date > hold_record.date and not h.hold_end_date
                    )
                    if not more_recent_holds:
                        # This is the active hold, calculate up to today
                        hold_end = today
                    else:
                        # There's a more recent hold, skip this one
                        continue
                else:
                    # Property is off hold but no end date - this shouldn't happen if OffHoldWizard worked
                    # Skip incomplete records
                    continue
                
                if hold_end >= hold_start:
                    total_days += (hold_end - hold_start).days
            
            record.days_on_pause = total_days
    
    def _compute_delayed_invoice_payments(self):
        """Calculate number of invoices with 3+ days of delay"""
        today = date.today()
        # Batch compute all_invoices first if needed
        projects = self.search([("address", "!=", False)])
        for record in projects:
            if not record.address or not record.address.analytical_account:
                record.delayed_invoice_payments = 0
                record.delayed_invoice_list = False
                continue

            invoice_lines = self.env["account.analytic.line"].search([("account_id", "=", record.address.analytical_account.id), ("category", "=", "invoice")]).mapped("move_line_id")
            invoices = invoice_lines.mapped("move_id")
            late_count = 0
            ontime_count = 0
            days_late = 0
            delayed_invoices = []
            ontime_invoices = []
            for invoice in invoices:
                days_delay = self._calculate_invoice_delay_days(invoice, today)
                if days_delay >= 3:
                    late_count += 1
                    days_late += (days_delay - 3)
                    delayed_invoices.append(invoice.id)
                else:
                    ontime_count += 1
                    ontime_invoices.append(invoice.id)


            record.write({
                "delayed_invoice_payments": late_count,
                "delayed_invoice_list": [(6,0,delayed_invoices)],
                "on_time_invoice_payments": ontime_count,
                "total_late_days": days_late,
                "on_time_invoice_list" : [(6,0,ontime_invoices)], 
            }) 
            
    
    def _calculate_invoice_delay_days(self, invoice, today):
        """Helper method to calculate days of delay for an invoice"""
        if not invoice.invoice_date_due:
            return 0
        
        date_paid = invoice.date_paid
        if isinstance(date_paid, datetime):
            date_paid = date_paid.date()
                
        if date_paid:
            # Invoice is paid: calculate delay at payment date
            if date_paid > invoice.invoice_date_due:
                return (date_paid - invoice.invoice_date_due).days
            else:
                return 0
        else:
            # Invoice is unpaid: calculate delay up to today
            if invoice.invoice_date_due < today:
                return (today - invoice.invoice_date_due).days
            else:
                return 0
    
    @api.depends('project_duration', 'days_on_pause')
    def _compute_total_effective_time(self):
        """Calculate total effective time (duration minus pause time)"""
        for record in self:
            if record.project_duration and record.days_on_pause:
                record.total_effective_time = max(0, record.project_duration - record.days_on_pause)
            elif record.project_duration:
                record.total_effective_time = record.project_duration
            else:
                record.total_effective_time = 0
    
    @api.depends('project_duration')
    def _compute_project_duration_display(self):
        """Format project duration with 'days' suffix"""
        for record in self:
            if record.project_duration:
                record.project_duration_display = f"{record.project_duration} days"
            else:
                record.project_duration_display = "0 days"
    
    @api.depends('days_on_pause')
    def _compute_days_on_pause_display(self):
        """Format days on pause with 'days' suffix"""
        for record in self:
            if record.days_on_pause:
                record.days_on_pause_display = f"{record.days_on_pause} days"
            else:
                record.days_on_pause_display = "0 days"
    
    @api.depends('total_effective_time')
    def _compute_total_effective_time_display(self):
        """Format total effective time with 'days' suffix"""
        for record in self:
            if record.total_effective_time:
                record.total_effective_time_display = f"{record.total_effective_time} days"
            else:
                record.total_effective_time_display = "0 days"

    def start_construction_button(self):
        for record in self:
            record.status_construction = "epp"
            property_status = record.env["pms.property"].search([("id", "=", record.address.id)])
            property_status.to_construction()

            # record.start_project = datetime.now()
            
    @api.depends("project_routes_lines.vendor", "project_routes_lines.order_date", "project_routes_lines.completed")
    def _next_jobsheader(self):
        for record in self:
            next_jobs = record.env["pms.projects.routes"].search(["&", ("project_property.id", "=", record.id), "&", ("order_date", "!=", False), ("completed", "=", False)])
            if next_jobs:
                next_job = record.env["pms.projects.routes"].search([("id", "=", next_jobs.ids[0])])
                record.next_activity = next_job.id
                record.next_orderdate = next_job.order_date
                record.next_vendor = next_job.vendor.name
            else:
                record.next_activity = False
                record.next_orderdate = False
                record.next_vendor = False




    @api.depends("start_project", "end_project")
    def _calculate_project_duration(self):
        for record in self:
            if record.start_project and record.end_project: 
                record.project_duration = (record.end_project - record.start_project).days
                if record.project_duration < 0:
                    record.project_duration = 0
            
            elif record.start_project:
                record.project_duration = (datetime.now() - record.start_project).days
                if record.project_duration < 0:
                    record.project_duration = 0
            else:
                record.project_duration = 0

    def back_to_pending(self):
        completed_activity = self.project_routes_lines.mapped("completed")
        if True in completed_activity:
            raise ValidationError("The project has activities that have been completed. It cannot be moved back to pending.")
        else:
            self.status_construction = "pending"
            self.end_project = ''
            self.project_completed = False
            self.project_routes_lines.unlink()
            self.project_routes = ''
    
    def request_draw(self):
            
        ctx = dict(active_ids=self.ids)
        
        request_draw_form = self.env.ref('pms.view_pms_request_draw_wizard_form')
        return {
                        'name': 'Draw Ref Wizard',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'pms.request.draw.wizard',
                        'views': [(request_draw_form.id, 'form')],
                        'view_id': request_draw_form.id,
                        'target': 'new',
                        'context': ctx}
    
        '''if self.address.loans:
                status_draw = self.address.loans.search(["&", ("exit_status", "!=", "refinanced"), ("property_address", "=", self.address.id)])
                if isinstance(status_draw.ids, list) and len(status_draw.ids) > 1:
                    raise ValidationError("The property has more than one active loan. Please select the loan to request the draw.") 
                else:
                   draw_draft = {
                        'name': self.name,
                        'loan_id': status_draw.id,
                        'draw_amount': '',
                        'draw_fee': '',
                        'memo': '',
                        'date': datetime.now(),
                        'status': 'draft'
                        }
                self.env["pms.draws"].create(draw_draft)
            else:    
                raise ValidationError("The property does not have a loan associated with it.")'''
#Function that checks if a property is already linked to a project
    @api.constrains('address')
    def check_property(self):
        for record in self:
            if record.address:
                check = record.env["pms.projects"].search(["&", ("address.id", "=", record.address.id), ("active", "!=", False), ("id", "!=", record.id)])
                if check:
                    raise ValidationError("The property is already linked to a project.")
                else:
                    pass
            else:
                pass
            
    def get_summary_view(self):
        self.ensure_one()
        ctx = {"property_project": self.id,
               "project_route": self.project_routes.id}
        return {
            'type': 'ir.actions.act_window',
            'name': ('project_summary_report_tree'),
            'res_model': 'pms.project.summary',
            'view_mode': 'tree',
            'context': ctx}

    def get_phase_times(self):
        self.ensure_one()
        ctx = {"property_project": self.id}
        return {
            'type': 'ir.actions.act_window',
            'name': ('pms_phase_time_tree'),
            'res_model': 'pms.phase.time',
            'view_mode': 'tree',
            'context': ctx}
    
    def open_visit_wizard(self):
        ctx = dict(
            active_ids=self.ids
            )
        
        visit_form = self.env.ref('pms.view_visit_days_wizard_form')
        return {
                'name': 'Visit Days Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'visit.days.wizard',
                'views': [(visit_form.id, 'form')],
                'view_id': visit_form.id,
                'target': 'new',
                'context': ctx}
    
    def open_visit_project_wizard(self):
        ctx = dict(
            active_ids=self.ids
            )
        
        visit_form = self.env.ref('pms.view_visit_projects_bulk_wizard_form')
        return {
                'name': 'Visit Days Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'visit.day.project.wizard',
                'views': [(visit_form.id, 'form')],
                'view_id': visit_form.id,
                'target': 'new',
                'context': ctx}
    
    def open_planned_visit_wizard(self):
        ctx = dict(
            active_ids=self.ids
            )
        
        visit_form = self.env.ref('pms.view_planned_visit_days_wizard_form')
        return {
                'name': 'Planned Visit Days Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'planned.visit.days.wizard',
                'views': [(visit_form.id, 'form')],
                'view_id': visit_form.id,
                'target': 'new',
                'context': ctx}

    def action_update_house_model(self):
        return {
            'name': 'Update House Model',
            'view_mode': 'form',
            'res_model': 'pms.projects.update.house.model',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }
    
    def action_recompute_invoice_fields(self):
        self._compute_delayed_invoice_payments()
        
class pms_projects_update_house_model(models.TransientModel):
    _name = "pms.projects.update.house.model"
    _description = "PMS Projects Update House Model"
    
    house_model = fields.Many2one("pms.housemodels", string="New House Model")
    
    def update_house_model(self):
        project_ids = self.env.context.get('active_ids', [])
        _logger.info("Project IDs: %s", project_ids)

        if project_ids:
            projects = self.env['pms.projects'].browse(project_ids) 
            project_count = len(projects)

            projects.write({'house_model': self.house_model.id}) 

            if project_count == 1:
                house_model_name = self.house_model.name
                message = _("House model '%s' successfully updated for %d project.") % (house_model_name, project_count)
            else:
                house_model_name = self.house_model.name
                message = _("House model '%s' successfully updated for %d projects.") % (house_model_name, project_count)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'info',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'}
                }
            }

    @api.model
    def _send_expiration_date_reminders(self):
        """
        Scheduled action to send email reminders for projects with expiration_date 
        that is due in 30 days (permits expiring soon).
        """
        _logger.info("Running scheduled action: _send_expiration_date_reminders")
        
        # Calculate the target date (30 days from today - permits expiring in 30 days)
        target_date = fields.Date.today() + timedelta(days=30)
        
        # Find projects with expiration_date equal to 3 days from now
        projects_to_remind = self.search([
            ('expiration_date', '=', target_date),
            ('status_construction', 'not in', ['completed', 'coc']),
        ])
        
        _logger.info(f"Found {len(projects_to_remind)} projects with expiration date on {target_date}")
        
        if not projects_to_remind:
            _logger.info("No projects found with expiration date in 3 days")
            return True
        
        # Get the email template
        template = self.env.ref('pms.email_template_project_expiration_reminder', raise_if_not_found=False)
        
        if not template:
            _logger.warning("Email template 'pms.email_template_project_expiration_reminder' not found")
            return False
        
        for project in projects_to_remind:
            try:
                # Send email using the template
                template.send_mail(project.id, force_send=True)
                _logger.info(f"Expiration reminder email sent for project: {project.name}")
            except Exception as e:
                _logger.error(f"Failed to send expiration reminder for project {project.name}: {str(e)}")
        
        return True
    
    @api.model
    def _get_expiration_reminder_recipients(self):
        """
        Get the list of email recipients for expiration reminders.
        Returns emails of project manager and superintendent if available.
        """
        recipients = []
        if self.project_manager and self.project_manager.work_email:
            recipients.append(self.project_manager.work_email)
        if self.superintendent and self.superintendent.work_email:
            recipients.append(self.superintendent.work_email)
        return ','.join(recipients) if recipients else ''


