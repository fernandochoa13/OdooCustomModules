from odoo.exceptions import UserError
from odoo import models, fields, api, exceptions, _
from urllib.parse import quote
import json
import re
import requests

import logging
_logger = logging.getLogger(__name__)
    
class pms_contractor_job(models.Model):
    _name = 'pms.contractor.job'
    _description = 'Contractor Jobs'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # readonly based on state, didnt work for some reason
    # states={'cancel': [('readonly', True)]}

    # PROPERTY FIELDS
    
    property_id = fields.Many2one('pms.property', string='Job Property', required=True)
    property_model = fields.Many2one(related='property_id.house_model', string='Property Model', readonly=True, store=True)
    property_city = fields.Many2one(related='property_id.city', string='Property City', readonly=True, store=True)
    own_third = fields.Selection(selection=[("own", "Own"), ("third", "Third")], related='property_id.own_third', store=True)

    on_hold_status = fields.Boolean(related='property_id.on_hold', string='Property On Hold', readonly=True, store=True)
    days_on_hold = fields.Integer(related='property_id.days_on_hold', string='Days On Hold', readonly=True, store=True)
    # property_superintendent = fields.Many2one(related='property_id.superintendent', string='Property Superintendent', readonly=True, store=True)
    property_status = fields.Selection(related='property_id.status_property', string='Property Status', readonly=True, store=True)
    property_owner = fields.Many2one(related='property_id.partner_id', string='Property Owner', readonly=True, store=True)
    property_custodial_money = fields.Boolean(related='property_id.custodial_money', string='Is Escrow Company', readonly=True, store=True)
    # property_county = fields.Many2one(related='property_id.county', string='Property County', readonly=True)
    
    superintendent = fields.Many2one(
        comodel_name="hr.employee",
        string="Superintendent",
        compute="_compute_superintendent",
        store=True, # To allow searching and grouping
        readonly=True # Set to True if it should never be edited
    )

    @api.depends('property_id.projects.superintendent')
    def _compute_superintendent(self):
        for record in self:
            if record.property_id and record.property_id.projects:
                record.superintendent = record.property_id.projects[0].superintendent
            else:
                record.superintendent = False
    
    # JOB FIELDS
    
    name = fields.Char(string='Job Name', required=True) # SACAR NAME Y DESCRIPTION DE UN DROP DOWN O DE OTRA TABLA
    description = fields.Char(string='Job Description')
    deadline = fields.Date(string='Deadline')
    maintenance_order = fields.Boolean(string='No Invoice Needed') # if maintenance_order, activity isnt required
    billable = fields.Boolean(string='Billable')
    state = fields.Selection([
        ('created', 'Created'),
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        # ('reordered', 'Reordered'),
    ], string='Status', default='created', tracking=True)
    active = fields.Boolean(string='Active', default=True, help="If unchecked, it will allow you to hide the job without deleting it.")
    # ZONE COORDINATOR ONLY FIELDS
    estimated_job_co_date = fields.Date(string='Estimated Completion Date')
    
    creation_date = fields.Datetime(string='Creation Date', default=fields.Datetime.now, readonly=True)
    order_date = fields.Datetime(string='Order Date')
    in_progress_date = fields.Datetime(string='In Progress Date', readonly=True) # NEW
    completed_date = fields.Datetime(string='Completed Date', readonly=True) # NEW
    # (ordered - created, completed - ordered, completed - in progress, completed - created)
    # CONTRACTOR DETAILS
    contractor_id = fields.Many2one('res.partner', string='Job Contractor')
    contractor_city = fields.Char(related='contractor_id.city', string="City")
    
    # NOTIFICATION FIELDS
    
    email_sent = fields.Boolean(string='Email Sent', default=False)
    sms_sent = fields.Boolean(string='SMS Sent', default=False)
    order_sent = fields.Boolean(string='Order Sent', readonly=True)
    ws_sent = fields.Boolean(string='WhatsApp Sent', default=False) # NEW manual 
    
    # BILLING FIELDS
    
    bill_created = fields.Boolean(string='Bill Created')
    bill_loaded = fields.Boolean(string='Bill Loaded')
    linked_bill = fields.Many2one('account.move', string='Linked Bill', readonly=True)
    
    company = fields.Many2one('res.company', string='Company', compute="_compute_invoice_partner", store=True, inverse="_inverse_invoice_partner")
    partner_invoice = fields.Many2one('res.partner', string='Invoice Partner', compute="_compute_invoice_partner", store=True, inverse ="_inverse_invoice_partner")
    is_3rd_party = fields.Boolean(string='Is 3rd Party', compute="_compute_3rd_party")
    skip_notify = fields.Boolean(string='Skip Notification', default=True, help="If checked, the job will not send notifications when the state changes.")
    
    # @api.depends('company', 'partner_invoice')
    # def _compute_3rd_party(self):
    #     for record in self:
            
    #         is_3rd_party_found = False
            
    #         companies = [
    #             "CFL Rehabbers",
    #             "CFL Construction",
    #             "Tetcho Roofing",
    #             "ADG Homes",
    #             "3rd party"
    #         ]

    #         company_name_lower = (record.company.name or '').lower()
    #         partner_invoice_name_lower = (record.partner_invoice.name or '').lower()

    #         for company_check in companies:
    #             company_check_lower = company_check.lower()
                
    #             if company_check_lower in company_name_lower:
    #                 is_3rd_party_found = True
    #                 break
                
    #             if company_check_lower in partner_invoice_name_lower:
    #                 is_3rd_party_found = True
    #                 break
            
    #         record.is_3rd_party = is_3rd_party_found
    
    must_use_logic = fields.Boolean(string='Partner Activity', default=False)
    logic = fields.Many2one('pms.contractor.logic', string="Logic")
    
    @api.depends("property_id", "property_id.custodial_money", "property_id.own_third", "property_id.partner_id", "property_id.status_property", "property_id.partner_id.company_id")
    def _compute_invoice_partner(self):
        for record in self:
            property_obj = record.property_id
            project = self.env['pms.projects'].search([('address', '=', property_obj.id)], limit=1)

            if property_obj.custodial_money:
                escrow_company = project.escrow_company if project and project.escrow_company else None
                partner = escrow_company.partner_id if escrow_company else None
                partner_id = partner.id if partner else None
                record.write({
                    'company': escrow_company.id,
                    'partner_invoice': partner_id,
                    'must_use_logic': False,
                })
                continue

            elif property_obj.own_third == 'own':
                partner_id = property_obj.partner_id.id if property_obj and property_obj.partner_id else None
                company = self.env['res.company'].search([('partner_id', '=', partner_id)], limit=1)
                company_id = company.id if company else None
                record.write({
                    'company': company_id, 
                    'partner_invoice': partner_id, 
                    'must_use_logic': False,
                })
                continue

            elif property_obj.own_third == 'third': 
                if property_obj.status_property == 'rented':
                    company = self.env['res.company'].browse(41)
                    record.write({
                        'company': company.id,
                        'partner_invoice': company.id,
                        'must_use_logic': False,
                    })
                    continue
                elif property_obj.status_property in ('construction', 'coc'):
                    record.must_use_logic = True
                    continue

    @api.onchange("logic")
    def logic_change(self):
        for record in self:
            logic = record.logic
            record.company = False
            record.partner_invoice = False
            if logic.company.id == 46:
                record.company = self.env['res.company'].browse(46)
            elif logic.company.id == 47:
                record.company = self.env['res.company'].browse(47)
            elif logic.company.id == 55:
                record.company = self.env['res.company'].browse(55)
                
            if logic.partner_invoice == "Owner":
                record.partner_invoice = record.property_id.partner_id
            elif logic.partner_invoice == "Company":
                record.partner_invoice = record.company.partner_id


    #    companies = [
    #         55, # CFL
    #         47, # ADG
    #         49, # Tetcho Roofing
    #     ]
    #     third_party_companies = [
    #         46, # 3rd Party
    #     ]

    def _inverse_invoice_partner(self):
        return
    
    linked_journal_entry = fields.Many2one('account.move', string='Linked Journal Entry', readonly=True)    
    linked_activity = fields.Many2one('pms.activity.costs', string='Linked Activity')
    estimated_cost = fields.Float(string='Estimated Cost', readonly=True, compute="_compute_estimated_cost")
    # linked_budget_model = fields.Many2one('budget.model', string='Linked Budget Model', readonly=True)
    linked_product = fields.Many2one('product.product', string='Linked Product', inverse="_inverse_linked_product") 
    
    def _inverse_linked_product(self):
        return

    # Computed field sacar product activity: budget model que tenga el activity, y de ahi el product con ese budget model?
    # tomar en cuenta city, county, etc.
    @api.depends('contractor_id', 'property_model', 'property_city', 'linked_activity')
    def _compute_estimated_cost(self):
        for record in self:
            record.estimated_cost = 0.0
            record.linked_product = False 

            if record.contractor_id and record.property_model and record.property_city:
                domain = [
                    ('supplier', '=', record.contractor_id.id),
                    ('house_model', '=', record.property_model.id),
                    ('city', '=', record.property_city.id),
                ]
                if record.linked_activity:
                    domain.append(('activity', '=', record.linked_activity.id))
                
                budget = self.env['budget.model'].search(domain, limit=1)
                _logger.info("Budget found for job '%s' (ID: %s): %s", record.name, record.id, budget.id if budget else 'None') 

                if budget and budget.amount:
                    record.estimated_cost = budget.amount
                    
                    if budget.product_model: 
                        product = self.env['product.product'].search([('name', 'ilike', budget.product_model.name)], limit=1)
                        if product:
                            record.linked_product = product.id

    linked_invoice = fields.Many2one('account.move', string='Linked Invoice', readonly=True)
    invoice_payment_state = fields.Selection(related='linked_invoice.payment_state', string='Invoice Payment State', readonly=True, store=True)
    
    # QUE SE CREE INVOICE PARA TODAS LAS EMPRESAS MENOS 3rd PARTY, ELIMINAR BOOLEAN DE create_invoice
    
    
    def generate_invoice(self):
        active_ids = self.env.context.get('active_ids', [])
        records = self.browse(active_ids)
        for record in records:
            
            is_3rd_party = False
            
            companies = [
                "3rd party"
            ]

            company_name_lower = (record.company.name or '').lower()

            for company_check in companies:
                company_check_lower = company_check.lower()
                
                if company_check_lower in company_name_lower:
                    is_3rd_party = True
                    break
                
            if is_3rd_party:
                return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Couldn't Create Invoice"),
                    'message': _("Cannot create an invoice for a 3rd party company."),
                    'sticky': True
                })
        
            if record.linked_invoice and record.invoice_payment_state not in ['cancel']:
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Couldn't Create Invoice"),
                    'message': _("Job already has a linked invoice. Please cancel it before creating a new one."),
                    'sticky': True
                })
                continue
            
            else:
                new_invoice = self.env['account.move'].sudo().create({
                    'move_type': 'out_invoice',
                    'linked_contractor_job': record.id,
                    'partner_id': record.property_id.partner_id.id if record.property_id and record.property_id.partner_id else False,
                    'company_id': record.company.id if record.company else False,
                    'invoice_date': fields.Date.today(),
                    'state': 'draft',
                    'payment_reference': 'Contractor job: ' + record.name,
                    'invoice_line_ids': [(0, 0, {
                        'analytic_distribution': {str(record.property_id.analytical_account.id): 100.0} if record.property_id and record.property_id.analytical_account else False,
                        'quantity': 1,
                        # 'product_id': record.linked_product.id,
                        # 'activity': record.linked_activity.id,
                        # 'name': f'Contractor Job: {record.name}',
                        # 'account_id': account,
                        # 'price_unit': record.estimated_cost
                    })]
                    # 'invoice_payment_term_id': payment_term.id if payment_term else False,
                })
                
                record.linked_invoice = new_invoice.id
            
                attachments_to_copy = self.env['ir.attachment'].search([
                    ('res_model', '=', record._name),
                    ('res_id', '=', record.id)
                ])

                for attachment in attachments_to_copy:
                    attachment.copy({
                        'res_model': 'account.move',
                        'res_id': new_invoice.id,
                    })
    
    
    # def set_pending(self):
    #     for record in self:
            
    #         company_match = False
    #         companies = [
    #             "CFL REHABBERS LLC",
    #             "ADG Homes, LLC",
    #         ]

    #         company_name_lower = (record.company.name or '').lower()
    #         partner_invoice_name_lower = (record.partner_invoice.name or '').lower()

    #         for company_check in companies:
    #             company_check_lower = company_check.lower()
                
    #             if company_check_lower in company_name_lower:
    #                 company_match = True
    #                 break
                
    #             if company_check_lower in partner_invoice_name_lower:
    #                 company_match = True
    #                 break
            
    #         if record.on_hold_status and not company_match: 
    #             self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
    #                 'type': 'warning',
    #                 'title': _("Permission Denied"),
    #                 'message': _("Cannot order a job for a property on hold.")
    #             })
    #             return False
            
    #         if record.state == 'created':
    #             record.generate_invoice()
    #             record.state = 'pending'
    #             record.state_change_notification()


    #         else:
    #             raise UserError(_("Job must be in 'Created' state to set it as Pending."))
    
    def _sync_attachments_with_invoice_or_bill(self):
        self.ensure_one()
        
        # Determine the target document (either an invoice or a bill)
        linked_move = self.linked_invoice or self.linked_bill
        
        if not linked_move:
            return

        # Search for attachments on the current record (the job)
        job_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id)
        ])

        # Search for attachments on the target document (invoice or bill)
        move_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', linked_move.id)
        ])

        # Add attachments from job to the target document
        job_att_identifiers = {(att.name, att.datas) for att in job_attachments}
        move_att_identifiers = {(att.name, att.datas) for att in move_attachments}

        for job_att in job_attachments:
            if (job_att.name, job_att.datas) not in move_att_identifiers:
                job_att.copy({
                    'res_model': 'account.move',
                    'res_id': linked_move.id,
                    'name': job_att.name,
                    'is_synced_from_job': True  # Mark this attachment as synced
                })

        # Remove attachments from the target document that were synced but are no longer on the job
        for move_att in move_attachments:
            if move_att.is_synced_from_job and (move_att.name, move_att.datas) not in job_att_identifiers:
                move_att.unlink()

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.linked_invoice or record.linked_bill:
                record._sync_attachments_with_invoice_or_bill()
        return res

    # linked_budget_activity = fields.Many2one('budget.model', string='Linked Activity')
    # estimated_cost = fields.Float(string='Estimated Cost', related='linked_budget_activity.amount')
    # @api.onchange("linked_budget_activity")
    # def _get_estimated_cost(self):
    #     for record in self:
    #         record.estimated_cost = record.linked_budget_activity.amount if record.linked_budget_activity else 0
    
    linked_project_activity = fields.Many2one('pms.projects.routes', string='Linked Project Activity')
    linked_project_activity_completed = fields.Boolean(related='linked_project_activity.completed', string='Linked Project Activity Completed', readonly=True, store=True)
    # , domain="['&', ('county', '=', property_county), ('vendor', '=', contractor_id)]"
    # linked_activity_domain = fields.Char(compute="_compute_linked_activity_domain", store=True)
    
    assigned_users = fields.Many2many('res.users', string='Assigned Users')
    
    reorder_count = fields.Integer(string='Reorder Count', default=0, readonly=True)


    # KPI1 :: Ordered --> Created 
    created_to_ordered = fields.Integer(default=0, readonly=True, string="Days from 'Created' to 'Ordered'", store=True, compute="_compute_created_to_ordered",
        help="""KPI1: Days between 'Creation Date' and 'Order Date' fields.""")

    # KPI2 :: In Progress --> Ordered
    ordered_to_in_progress = fields.Integer(default=0, readonly=True, string="Days from 'Ordered' to 'In Progress'", store=True, compute="_compute_ordered_to_in_progress",
        help="""KPI2: Days between 'Order Date' and 'In Progress Date' fields.""")

    # KPI3 :: Completed --> In Progress
    in_progress_to_completed = fields.Integer(default=0, readonly=True, string="Days from 'In Progress' to 'Completed'", store=True, compute="_compute_in_progress_to_completed",
        help="""KPI3: Days between 'In Progress Date' and 'Completed Date' fields.""")

    # KPI4 :: Completed --> Created
    created_to_completed = fields.Integer(default=0, readonly=True, string="Days from 'Created' to 'Completed'", store=True, compute="_compute_created_to_completed",
        help="""KPI4: Days between 'Creation Date' and 'Completed Date' fields.""")

    active = fields.Boolean(string='Active', default=True, help="If unchecked, it will allow you to hide the job without deleting it.")

    @api.depends('order_date', 'creation_date')
    def _compute_created_to_ordered(self):
        for record in self:
            if record.order_date and record.creation_date:
                record.created_to_ordered = (record.order_date - record.creation_date).days
            else:
                record.created_to_ordered = 0

    @api.depends('in_progress_date', 'order_date')
    def _compute_ordered_to_in_progress(self):
        for record in self:
            if record.in_progress_date and record.order_date:
                record.ordered_to_in_progress = (record.in_progress_date - record.order_date).days
            else:
                record.ordered_to_in_progress = 0

    @api.depends('completed_date', 'in_progress_date')
    def _compute_in_progress_to_completed(self):
        for record in self:
            if record.completed_date and record.in_progress_date:
                record.in_progress_to_completed = (record.completed_date - record.in_progress_date).days
            else:
                record.in_progress_to_completed = 0

    @api.depends('completed_date', 'creation_date')
    def _compute_created_to_completed(self):
        for record in self:
            if record.completed_date and record.creation_date:
                record.created_to_completed = (fields.Datetime.to_datetime(record.completed_date) - record.creation_date).days
            else:
                record.created_to_completed = 0
            
    # @api.depends('contractor_id', 'property_model', 'property_city')
    # def _compute_linked_activity_domain(self):
    #     for record in self:
    #         domain = [('id', '=', False)]  # Default to empty domain
    #         supplier = record.contractor_id
    #         house_model = record.property_model
    #         city = record.property_city

    #         budget_model = self.env['budget.model']
    #         if budget_model:
    #             budget_activity_ids = budget_model.search([
    #                 ('supplier', '=', supplier.id),
    #                 ('house_model', '=', house_model.id),
    #                 ('city', '=', city.id),
    #             ]).mapped('activity').ids
    #             domain = [('id', 'in', budget_activity_ids)]
    #         else:
    #             domain = [('id', '=', False)] # return empty domain
    #         record.linked_activity_domain = json.dumps(domain)      
            
    # @api.onchange("linked_project_activity", "property_model", "contractor_id")
    # def _get_estimated_cost(self):
    #     self.ensure_one()

    #     # activity = self.linked_project_activity.name.activity
    #     supplier = self.contractor_id
    #     house_model = self.property_model
    #     # county = self.property_county
    #     city = self.property_city

    #     budget = self.env['budget.model'].search([
    #         # ('activity', '=', activity.id),
    #         ('supplier', '=', supplier.id),
    #         ('house_model', '=', house_model.id),
    #         ('city', '=', city.id),
    #     ], limit=1)
        
    #     # Since activity is empty, estimated_cost could be a many2one field that filters based on the contractor_id, city
    #     # and house_model, and the user selects the appropriate cost

    #     if budget:
    #         self.estimated_cost = budget.amount
    #     else:
    #         self.estimated_cost = False
            
    #     return


    # COST FIELDS
    
    """
    Precio estimado para cada actividad en base a modelo de casa
    - En algunos casos el job tendra un precio determinado automatico en base a esta tabla
    
    linked_project_activity -> pms.projects.routes -> "name" Many2one("pms.projects.routes.templates.lines" -> activity = fields.Many2one("pms.activity.costs"
    
    to find the cost we use:
    activity = self.linked_project_activity.name.activity
    self.property_model
    
    to search the budget_model
    contractor_id = supplier
    
    """
    # PENDING FUNCTIONALITY
    
    """
    linked activity with accounting wizard (jobs, activities)
    Project activity: update when order is created
    Company selection rules: company, billable, cuenta contable
     - En base de reglas se llena compania automatico y datos en pdf
    Cuenta contable field
    Vista para contratistas para ver sus trabajos y cargar sus bills
     - Cargar bill: contratista entra a portal, busca orden y sube factura
    Opcion de devolver bill (contabilidad) 
     - envia mensaje a contratista y le dice que lo vuelva a cargar
     - Si se cancela un bill, reembolso
     Contabilidad:
      - registrar cuando llega el trabajo
       - si creas el bill primero y despues te lo completa perfecto
       - si te hicieron el trabajo y no tienes bill
        - se debe registrar automatico para crear el gasto de ese trabajo
        - cuando llegue el bill, ajustando o reemplazando el registro automatico para que quede como el principal
        - en caso de que se de completed y no hay bill
    """
    def open_action(self):
        action_view = self.env.ref('pms.view_pms_contractor_job_form')
        return {
            'name': 'Contractor Job',
            'type': 'ir.actions.act_window',
            'res_model': 'pms.contractor.job',
            'view_mode': 'form',
            'view_id': action_view.id,
            'res_id': self.id,
            'target': 'current',
        }
        
    def send_message_team(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Message',
            'res_model': 'send.order.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'model': self._name,
            }
        }    

    # @api.onchange("linked_project_activity")
    # def update_linked_activity(self):
    #     return
    
    def view_order_job(self):
        group = 'pms.group_account_manager'
        if not self.env.user.has_group(group): 
            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Permission Denied"),
                'message': _("Only Zone Coordinators have permission to order jobs.")
            })

        
        company_match = False
        companies = [
            "CFL Rehabbers",
            "ADG Homes",
        ]

        company_name_lower = (self.company.name or '').lower()
        partner_invoice_name_lower = (self.partner_invoice.name or '').lower()

        for company_check in companies:
            company_check_lower = company_check.lower()
            
            if company_check_lower in company_name_lower:
                company_match = True
                break
            
            if company_check_lower in partner_invoice_name_lower:
                company_match = True
                break
        
        if self.on_hold_status and not company_match: 
            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Permission Denied"),
                'message': _("Cannot order a job for a property on hold.")
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Order Job',
            'res_model': 'pms.contractor.job.order.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': self.name,
                'default_description': self.description,
                'default_deadline': self.deadline,
                'default_property_city': self.property_city.id,
                'default_property_id': self.property_id.id,
                'default_job_id': self.id
            }
        }

    def skip_notification(self):
        for job in self:
            
            if job.maintenance_order:
                job.write({
                    'state': 'in_progress',
                    'order_sent': True,
                    'skip_notify': True,
                })
                return
            
            company_match = False
            companies = [
                "CFL Rehabbers",
                "ADG Homes",
            ]

            company_name_lower = (self.company.name or '').lower()
            partner_invoice_name_lower = (self.partner_invoice.name or '').lower()

            for company_check in companies:
                company_check_lower = company_check.lower()
                
                if company_check_lower in company_name_lower:
                    company_match = True
                    break
                
                if company_check_lower in partner_invoice_name_lower:
                    company_match = True
                    break
            
            if self.on_hold_status and not company_match: 
                return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Permission Denied"),
                    'message': _("Cannot order a job for a property on hold.")
                })
                
            # if job.is_3rd_party:
            if job.linked_invoice and job.invoice_payment_state in ['paid', 'in_payment']:
                job.write({
                    'state': 'in_progress',
                    'order_sent': True,
                    'skip_notify': True,
                })
            elif job.linked_bill:
                job.write({
                    'state': 'in_progress',
                    'order_sent': True,
                    'skip_notify': True,
                })
            else:
                message = "The linked invoice must be paid before starting the job."
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Warning"),
                    'message': message,
                    'sticky': True
                })
            # else:
            #     job.write({
            #         'state': 'in_progress',
            #         'order_sent': True,
            #         'skip_notify': True,
            #     })
                
    def toggle_state_change_notification(self):
        for record in self:
            record.skip_notify = not record.skip_notify    
    
    def state_change_notification(self):
        _logger.info("Running state_change_notification...")
        for record in self:
            
            if record.skip_notify:
                _logger.info("Skip notification for job: %s", record.name)
                continue
            
            recipient_emails = set()
            invalid_recipients_info = []
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

            if record.partner_invoice:
                if record.partner_invoice.email:
                    if re.match(email_regex, record.partner_invoice.email):
                        recipient_emails.add(record.partner_invoice.email)
                    else:
                        invalid_recipients_info.append(f"Invoice Partner ({record.partner_invoice.name}): {record.partner_invoice.email}")
                else:
                    invalid_recipients_info.append(f"Invoice Partner ({record.partner_invoice.name}): No email address found")

            for user in record.assigned_users:
                if user.email:
                    if re.match(email_regex, user.email):
                        recipient_emails.add(user.email)
                    else:
                        invalid_recipients_info.append(f"Assigned User ({user.name}): {user.email}")
                else:
                    invalid_recipients_info.append(f"Assigned User ({user.name}): No email address found")

            if recipient_emails:
                email_to = ",".join(recipient_emails)
                email_body = f"""
                    <html>
                        <head>
                            <meta charset="UTF-8">
                            <title>Job Status Updated!</title>
                        </head>
                        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f8f8; padding: 20px; margin: 0;">
                            <div style="background-color: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); max-width: 600px; margin: 20px auto;">
                                <h1 style="color: #007bff; font-size: 28px; margin-bottom: 20px; text-align: center;">The job '{record.name}' status has been updated to {record.state}.</h1>
                            </div>
                        </body>
                    </html>
                """

                mail_values = {
                    'subject': f'Job {record.name} Status Updated',
                    'body_html': email_body,
                    'email_to': email_to,
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
            else:
                message = f"No valid recipient emails found for job '{record.name}'."
                self.env['update.owner.call.day'].simple_notification("warning", 'Failed to send email notification.', message, True)

            if invalid_recipients_info:
                message = f"The following users/partners on job '{record.name}' will not be notified due to invalid or missing email addresses: {', '.join(invalid_recipients_info)}"
                self.env['update.owner.call.day'].simple_notification("warning", 'Failed to send email notification.', message, True)
                




    def view_notify_job(self):
        group = 'pms.group_account_manager' # Replace with correct group
        if not self.env.user.has_group(group):
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Permission Denied"),
                'message': _("Only Zone Coordinators have permission to notify jobs.")
            })
            return False
        if self.on_hold_status: 
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Permission Denied"),
                'message': _("Cannot notify a job for a property on hold.")
            })
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Notify Job',
            'res_model': 'pms.contractor.notify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contractor_id': self.contractor_id.id,
                'default_job_id': self.id,
                'default_sms_sent': self.sms_sent,
                'default_email_sent': self.email_sent
            }
        }
    
    def cancel_job(self):
        active_ids = self.env.context.get('active_ids', [])
        records = self.browse(active_ids)

        for record in records:
            if record.state in ['cancelled', 'completed'] or record.linked_invoice or record.linked_bill:
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Warning"),
                    'message': "Job is already cancelled or completed or has an invoice or bill. record: %s" % record.name
                })
                continue

            else:
                vals = {
                    'state': 'cancelled',
                    'bill_created': False,
                    'email_sent': False,
                    'sms_sent': False,
                    'order_sent': False,
                }

                if record.linked_bill and record.linked_bill.state in ['draft']:
                    _logger.info("Job has linked bill. cancelling bill %s", record.linked_bill.id)
                    bill = record.linked_bill
                    bill.button_cancel()
                    vals['linked_bill'] = False
                
                if record.linked_invoice and record.linked_invoice.state in ['draft']:
                    _logger.info("Job has linked invoice. cancelling invoice %s", record.linked_invoice.id)
                    invoice = record.linked_invoice
                    invoice.button_cancel()
                    vals['linked_invoice'] = False

                record.write(vals)
                record.state_change_notification()
                _logger.info("Job cancelled successfully. record: %s", record.id)
    
    def redo_job(self):
        for record in self:
            record.write({
                'state': 'created',
                'reorder_count': self.reorder_count + 1
                })
            record.state_change_notification()
            
        return
    
    def job_in_progress(self):
        records_to_update = self.env[self._name]
        
        for record in self:
            if record.maintenance_order:
                records_to_update += record
                continue 
                
            elif (record.linked_invoice and record.linked_invoice.payment_state != 'paid') or not record.linked_bill:
                return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Permission Denied"),
                    'message': _("The invoice for jobs must be paid before ordering.")
                })
            
            else:
                records_to_update += record

        if records_to_update:
            records_to_update.write({
                'state': 'in_progress',
                'in_progress_date': fields.Datetime.now(),
            })
            records_to_update.state_change_notification()

        return
    
    def complete_job(self):
        for record in self:
            record.write({
                'state': 'completed',
                'completed_date': fields.Datetime.now(),
                })
            if record.bill_created == True and record.linked_bill:
                record.linked_bill.activity_completed = True
        return

    def create_bill(self):
        _logger.info("Running create_bill...")
        active_ids = self.env.context.get('active_ids', [])
        records = self.browse(active_ids)
        companies = [
            42, # CFL
            47, # ADG
            49, # Tetcho Roofing
        ]
        third_party_companies = [
            46, # 3rd Party
        ]
        
        for record in records:
            property = record.property_id
            company = record.company
            _logger.info("company id: %s", company.id)
            if record.state not in ['ordered', 'in_progress', 'completed']:
                message = "Job must be in 'Ordered', 'In Progress', or 'Completed' to create a bill."
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Warning"),
                    'message': message,
                    'sticky': True
                })
                return
            if not property:
                message = "Property not found. Couldn't create bill."
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Warning"),
                    'message': message,
                    'sticky': True
                })
                return
            if not company:
                _logger.info("Company not found...")
                message = "Company not found. Couldn't create bill."
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Warning"),
                    'message': message,
                    'sticky': True
                })
                return
                
            if record.bill_created and record.linked_bill:
                _logger.info("Bill already exists...")
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Vendor Bill',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'res_id': record.linked_bill.id,
                    'target': 'current',
                }
            if property.own_third == "own" and company.partner_id == property.partner_id:
                _logger.info("Creating bill for own property...")
                if (property.status_property in ['construction']) or (property.status_property in ['coc'] and property.available_for_rent == False):
                    _logger.info("Creating bill for construction or coc property...")
                    account = record.env['account.account'].search([
                        ('company_id', "=", record.company.id), 
                        ('tag_ids', 'in', self.env['account.account.tag'].search([('name', '=', 'Direct Acquisition')]).ids), 
                        ('deprecated', '!=', True)
                    ], limit=1).id
                    if not account:
                        raise exceptions.UserError('No account found for direct acquisition.')
                    bill = self.env['account.move'].sudo().create({
                        'move_type': 'in_invoice',
                        'partner_id': record.contractor_id.id,
                        'company_id': record.company.id,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': record.estimated_job_co_date,
                        'linked_activities': record.linked_project_activity.id if record.linked_project_activity else False,
                        'activity_completed': record.linked_project_activity_completed,
                        'state': 'draft',
                        'payment_reference': record.name,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': record.linked_product.id,
                            'activity': record.linked_activity.id,
                            'name': f'Job: {record.name}',
                            'account_id': account,
                            'analytic_distribution': {str(record.property_id.analytical_account.id): 100.0},
                            'quantity': 1,
                            'price_unit': record.estimated_cost if record.estimated_cost else 0
                        })]
                    })
                    record.linked_bill = bill.id
                    record.bill_created = True
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Vendor Bill',
                        'res_model': 'account.move',
                        'view_mode': 'form',
                        'res_id': bill.id,
                        'target': 'current',
                    }
                elif (property.status_property in ['rented']) or (property.status_property in ['coc'] and property.available_for_rent == True):
                    _logger.info("Creating bill for rented property...")
                    account = self.env['account.account'].search([
                        ('company_id', '=', record.company.id), 
                        ('tag_ids', 'in', self.env['account.account.tag'].search([('name', '=', 'Repairs and Maintenance')]).ids), 
                        ('deprecated', '!=', True)
                    ], limit=1).id
                    if not account:
                        raise exceptions.UserError('No account found for repairs and maintenance.')    
#                 linked_project_activity
# linked_project_activity_completed
                    bill = self.env['account.move'].sudo().create({
                        'move_type': 'in_invoice',
                        'partner_id': record.contractor_id.id,
                        'company_id': record.company.id,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': record.estimated_job_co_date,
                        'linked_activities': record.linked_project_activity.id if record.linked_project_activity else False,
                        'activity_completed': record.linked_project_activity_completed,
                        'state': 'draft',
                        'payment_reference': record.name,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': record.linked_product.id,
                            'activity': record.linked_activity.id,
                            'name': f'Job: {record.name}',
                            'account_id': account,
                            'analytic_distribution': {str(record.property_id.analytical_account.id): 100.0},
                            'quantity': 1,
                            'price_unit': record.estimated_cost if record.estimated_cost else 0
                        })]
                    })
                    record.linked_bill = bill.id
                    record.bill_created = True
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Vendor Bill',
                        'res_model': 'account.move',
                        'view_mode': 'form',
                        'res_id': bill.id,
                        'target': 'current',
                    }
            elif property.own_third == "third":
                _logger.info("Creating bill for third party property...")
                if company.id in third_party_companies:
                    _logger.info("Creating bill for third party company...")
                    bill = self.env['account.move'].sudo().create({
                        'move_type': 'in_invoice',
                        'partner_id': record.contractor_id.id,
                        'company_id': record.company.id,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': record.estimated_job_co_date,
                        'linked_activities': record.linked_project_activity.id if record.linked_project_activity else False,
                        'activity_completed': record.linked_project_activity_completed,
                        'state': 'draft',
                        'payment_reference': record.name,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': record.linked_product.id,
                            'activity': record.linked_activity.id,
                            'name': f'Job: {record.name}',
                            # 'account_id': account,
                            'analytic_distribution': {str(record.property_id.analytical_account.id): 100.0},
                            'quantity': 1,
                            'price_unit': record.estimated_cost if record.estimated_cost else 0
                        })]
                    })
                    record.linked_bill = bill.id
                    record.bill_created = True
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Vendor Bill',
                        'res_model': 'account.move',
                        'view_mode': 'form',
                        'res_id': bill.id,
                        'target': 'current',
                    }
                    
                elif company.id in companies:
                    # deberia asignar account default if product
                    # else: cada compania tiene una cuenta predeterminada cuando se crea un bill
                    _logger.info("Creating bill for third party company 2...")
                    bill = self.env['account.move'].sudo().create({
                        'move_type': 'in_invoice',
                        'partner_id': record.contractor_id.id,
                        'company_id': record.company.id,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': record.estimated_job_co_date,
                        'linked_activities': record.linked_project_activity.id if record.linked_project_activity else False,
                        'activity_completed': record.linked_project_activity_completed,
                        'state': 'draft',
                        'payment_reference': record.name,
                            'invoice_line_ids': [(0, 0, {
                                'product_id': record.linked_product.id,
                                'activity': record.linked_activity.id,
                                'name': f'Job: {record.name}',
                                # 'account_id': account,
                                'analytic_distribution': {str(record.property_id.analytical_account.id): 100.0},
                                'quantity': 1,
                                'price_unit': record.estimated_cost if record.estimated_cost else 0
                            })]
                        })
                    record.linked_bill = bill.id
                    record.bill_created = True
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Vendor Bill',
                        'res_model': 'account.move',
                        'view_mode': 'form',
                        'res_id': bill.id,
                        'target': 'current',
                    }
                else:
                    message = "Company not found in specified allowed companies..."
                    self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                        'type': 'warning',
                        'title': _("Warning"),
                        'message': message,
                        'sticky': True
                    })
                return
            else:
                message = "No conditions met for creating bill..."
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'warning',
                    'title': _("Warning"),
                    'message': message,
                    'sticky': True
                })

#  !urgent  -- Fill product with activity and fill activity
 
    # @api.model
    # def create(self, vals):
    #     property = self.env['pms.property'].browse(vals['property_id'])
    #     if property.on_hold:
    #         raise exceptions.UserError('Cannot assign a job to a property that is on hold.')
    #     job = super(pms_contractor_job, self).create(vals)
    #     return job
    
    
class pms_contractor_notify_wizard(models.TransientModel):
    _name = 'pms.contractor.notify.wizard'
    _description = 'Contractor Notify Wizard'
    
    job_id = fields.Many2one('pms.contractor.job', string='Job', readonly=True)    
    contractor_id = fields.Many2one('res.partner', string='Job Contractor', readonly=True)
    contractor_phone = fields.Char(related='contractor_id.phone', string='Contractor Phone', readonly=True)
    contractor_email = fields.Char(related='contractor_id.email', string='Contractor Email', readonly=True)
    change_phone = fields.Boolean(string='Use different number?', compute='_compute_change_fields')
    change_email = fields.Boolean(string='Use different e-mail?', compute='_compute_change_fields')
    new_phone = fields.Char(string='New Phone')
    new_email = fields.Char(string='New Email')
    preview_email = fields.Html(string='Preview Email', compute='_compute_preview')
    preview_message = fields.Html(string='Preview Message', compute='_compute_preview')
    preview = fields.Boolean(string='Preview', default=False)
    custom_message = fields.Text(string='Custom Message', compute='_compute_default_message', readonly=False)

    email_sent = fields.Boolean(string='Email Sent', readonly=True)
    sms_sent = fields.Boolean(string='SMS Sent', readonly=True)
    
    email_template = fields.Many2one('mail.template', string='Email Template', domain="[('model', '=', 'pms.contractor.job')]")
    
    def open_whatsapp(self):
        phone = self.new_phone if self.change_phone and self.new_phone else self.contractor_phone
        
        cleaned_phone = self.clean_and_validate_phone(phone)

        if not cleaned_phone:
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Warning"),
                'message': f"Invalid phone format: {phone}"
            })
            return

        cleaned_phone = re.sub(r"[-\s\(\)]", "", phone)
        encoded_message = quote(self.custom_message)
        whatsapp_url = f"https://wa.me/{cleaned_phone}/?text={encoded_message}"
        job = self.job_id
        if job.ws_sent == False:
            job.ws_sent = True
        
        return {
            'type': 'ir.actions.act_url',
            'url': whatsapp_url,
            'target': 'new',
        }
        
    @api.depends('contractor_phone', 'contractor_email')
    def _compute_change_fields(self):
        for record in self:
            record.change_phone = not record.contractor_phone
            record.change_email = not record.contractor_email
    
    @api.depends('job_id')
    def _compute_default_message(self):
        for record in self:
            if record.job_id:
                job = record.job_id

                message = f"""Hello, {self.contractor_id.name}!

There is a new job for you, here are the details:

Job Name: {job.name}
Property: {job.property_id.name}
Property Model: {job.property_model.name if job.property_model else 'N/A'}
Property City: {job.property_id.city.name if job.property_id.city else 'N/A'}
Job Description: {job.description if job.description else 'N/A'}
Invoice to: {job.partner_invoice.name if job.partner_invoice else 'N/A'}
Deadline: {job.deadline if job.deadline else 'N/A'}

*This is an automated message.*"""

                record.custom_message = message
            else:
                record.custom_message = False



    def clean_and_validate_phone(self, phone):
        if not phone:
            return None

        cleaned_phone = re.sub(r"[-\s\(\)]", "", phone)
        phone_regex = r"^\+?\d{0,3}\d{7,14}$"

        if re.match(phone_regex, cleaned_phone):
            if not cleaned_phone.startswith("+"):
                cleaned_phone = "+" + cleaned_phone
            return cleaned_phone
        else:
            return None

    def send_notification_in_progress(self):
        self.send_notification()
        job = self.job_id
        # if job.is_3rd_party:
        if job.linked_invoice and job.invoice_payment_state in ['paid', 'in_payment']:
            job.state = 'in_progress'
        else:
            message = "The linked invoice must be paid before starting the job."
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Warning"),
                'message': message,
                'sticky': True
            })
        # else:    
        #     job.state = 'in_progress'
            

            

    def send_notification(self):

        job = self.job_id
        notes = f'''
            <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                <b>Job notification sent to contractor.</b>
            </div>
        '''
        job.message_post(body=notes)
        contractor = self.contractor_id
        email = self.new_email if self.new_email else contractor.email
        phone = self.new_phone if self.new_phone else contractor.phone

        errors = []

        # Email Sending
        if self.email_template and email and not job.email_sent:
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(email_regex, email):
                template = self.env['mail.template'].browse(self.email_template.id)
                email_values = {
                    'email_to': email,
                    'email_from': self.env.user.email,
                }
                sent_mail_ids = template.send_mail(self.job_id.id, force_send=True, email_values=email_values)
                _logger.info(f"Sent mail IDs: {sent_mail_ids}")

                job.email_sent = True
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'info',
                    'title': _("Success"),
                    'message': f"Email sent using template '{template.name}' to {email}"
                })
            else:
                errors.append(f"Invalid email format: {email}")
        elif email and not self.email_template and not job.email_sent:
            email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if re.match(email_regex, email):
                mail_values = {
                    'subject': f'New Job For You: {job.name}',
                    'body_html': self.preview_email,
                    'email_to': email,
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
                job.email_sent = True
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'info',
                    'title': _("Success"),
                    'message': f"Email sent to {email}"
                })
            else:
                errors.append(f"Invalid email format: {email}")
        elif job.email_sent:
            errors.append(f"Email was already sent.")
        elif not email:
            errors.append("Contractor email is not set.")

        # SMS Sending
        if phone and not job.sms_sent:
            cleaned_phone = self.clean_and_validate_phone(phone)
            if cleaned_phone:
                access_token = self.env['sms.silvamedia'].search([], limit=1).access_token
                message = self.custom_message
                contact_id = "NN9TQ5PNiBCAfOspmBFx"
                numbers = [cleaned_phone]

                for number in numbers:
                    try:
                        new_sms = requests.post("https://services.leadconnectorhq.com/conversations/messages",
                                                    json={'contactId': contact_id, 'message': message, 'toNumber': number, 'type': 'SMS'},
                                                    headers={'Authorization': f'Bearer {access_token}', 'Version': '2021-07-28', 'Content-Type': 'application/json', 'Accept': 'application/json'})

                        print(new_sms.json())
                        new_sms.raise_for_status()
                        self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                            'type': 'info',
                            'title': _("Success"),
                            'message': f"SMS sent to {number}"
                        })
                        job.write({'sms_sent': True})
                    except requests.exceptions.RequestException as e:
                        errors.append(f"Failed to send SMS: {e}")
            else:
                errors.append(f"Invalid phone format: {phone}")
        elif job.sms_sent:
            errors.append(f"SMS was already sent.")
        elif not phone:
            errors.append("Contractor phone number is not set.")

        if job.email_sent and job.sms_sent:
            job.order_sent = True
            return {'type': 'ir.actions.act_window_close'}

        if errors:
            message = 'The following errors occurred:\n\n%s' % '\n'.join(errors)
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'warning',
                'title': _("Warning"),
                'message': message,
                'sticky': True
            })

    @api.depends('email_template', 'job_id', 'contractor_id', 'custom_message')
    def _compute_preview(self):
        for record in self:
            if record.email_template and record.job_id and record.contractor_id:
                try:
                    template = record.env['mail.template'].browse(record.email_template.id)
                    record.preview_email = template.body_html
                    record.preview_message = f"""
                        <div style="background-color: #e8f5e9; border: 1px solid #a5d6a7; padding: 10px; border-radius: 4px; color: #388e3c;">
                            {record.preview_email or ''}
                        </div>
                    """
                except Exception as e:
                    record.preview_email = f"""
                        <div style="color: red;">
                            Error rendering template: {e}
                        </div>
                    """
                    record.preview_message = f"""
                        <div style="color: red;">
                            Error rendering template: {e}
                        </div>
                    """
            else:
                email_message = record.custom_message.replace("\n", "<br>")
                record.preview_email = f"""
                    <html>
                        <head>
                            <meta charset="UTF-8">
                            <title>New Job Created!</title>
                        </head>
                        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f8f8; padding: 20px; margin: 0;">
                            <div style="background-color: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); max-width: 600px; margin: 20px auto;">
                                <h1 style="color: #007bff; font-size: 28px; margin-bottom: 20px; text-align: center;">New Job For You</h1>
                                <p><span style="font-weight: bold; color: #28a745;">{email_message}</span></p>
                            </div>
                        </body>
                    </html>
                """
                record.preview_message = f"""
                    <div style="background-color: #e8f5e9; border: 1px solid #a5d6a7; padding: 10px; border-radius: 4px; color: #388e3c;">
                        {email_message}
                    </div>
                """

class pms_contractor_login_wizard(models.TransientModel):
    _name = 'pms.contractor.login.wizard'
    _description = 'Contractor Login Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='PIN', required=True)

    def action_login(self):
        self.ensure_one()

        if self.employee_id.pin != self.employee_pin:
            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'danger',
                'title': _("Warning"),
                'message': _('Incorrect pin for %s.', self.employee_id.name)
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Contractors',
            'res_model': 'pms.contractor.job',
            'view_mode': 'kanban,tree,form,calendar',
            'target': 'main',
        }

class pms_contractor_job_order_wizard(models.TransientModel):
    _name = 'pms.contractor.job.order.wizard'
    _description = 'Contractor Job Order Wizard'
        
    # READONLY FIELDS
    job_id = fields.Many2one('pms.contractor.job', string='Job', readonly=True)    
    name = fields.Char(string='Job Name', readonly=True)
    description = fields.Char(string='Job Description', readonly=True)
    property_id = fields.Many2one('pms.property', string='Job Property', readonly=True)
    property_city = fields.Many2one(related='property_id.city', string='Property City', readonly=True)
    deadline = fields.Date(string='Deadline', readonly=True)
    
    # NEW FIELDS
    contractor_id = fields.Many2one('res.partner', string='Job Contractor', required=True)
    order_date = fields.Datetime(string='Order Date', required=True)
    estimated_job_co_date = fields.Date(string='Estimated Completion Date', required=True)
    logic = fields.Many2one('pms.contractor.logic', string="Logic")
    must_use_logic = fields.Boolean(related="job_id.must_use_logic", string="Must Use Logic", readonly=True)

    def action_order_job(self):
        job = self.job_id
        job.write({
            'state': 'ordered',
            'order_date': self.order_date,
            'contractor_id': self.contractor_id.id,
            'estimated_job_co_date': self.estimated_job_co_date,
            'logic': self.logic.id,
            })
        job.state_change_notification()
        if job.must_use_logic:
            job.logic_change()
        return
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Notify Job',
        #     'res_model': 'pms.contractor.notify.wizard',
        #     'view_mode': 'form',
        #     'target': 'new',
        #     'context': {
        #         'default_contractor_id': self.contractor_id.id,
        #         'default_job_id': self.job_id.id
        #     }
        # }
        
class pms_contractor_logic(models.Model):
    _name = "pms.contractor.logic"
    _description = 'Contractor Job Logic'
    _rec_name = 'product'
    
    partner = fields.Many2one('res.partner', string='Contractor')
    payment_method = fields.Char(string='Payment Method')
    product = fields.Char(string='Product')
    first_party = fields.Char(string='First Party')
    third_party = fields.Char(string='Third Party')
    company = fields.Many2one('res.company', string='Company')
    partner_invoice = fields.Char(string='Invoice Partner')
    escrow_money = fields.Char(string='Escrow Money')
    on_hold = fields.Boolean(string='On Hold')

    # payment_method = fields.Selection([
    #     ("check", "Check"), ("tdc", "Credit Card"), ("ach", "ACH")
    # ], string='Payment Method')
    # product = fields.Many2one('product.product', string='Product')
    # first_party = fields.Selection([
    #     ("register_1st_party", "REGISTER IN 1ST PARTY"),
    #     ("tdc_auto", "TDC AUTO (EXPENSES)")
    # ], string='First Party')
    # third_party = fields.Selection([
    #     ("direct_3rd_party", "DIRECT 3RD PARTY"),
    #     ("cfl_billable", "CFL BILLABLE"),
    #     ("cfl_non_billable", "CFL NON BILLABLE"),
    #     ("cfl_facturable_service", "CFL FACTURABLE SERVICE"),
    #     ("cfl_facturable_service_non_billable", "CFL FACTURABLE SERVICE NON BILLABLE"),
    #     ("adg_billable", "ADG BILLABLE"),
    #     ("adg_facturable_service", "ADG FACTURABLE SERVICE"),
    #     ("adg_facturable_service_non_billable", "ADG FACTURABLE SERVICE NON BILLABLE"),
    #     ("gl_capital", "GL CAPITAL"),
    #     ("3rd_party_direct_card_payment", "3RD PARTY DIRECT CARD PAYMENT"),
    #     ], string='Third Party')
    
            # def create_bill(self):
    #     _logger.info("Running create_bill...")
    #     active_ids = self.env.context.get('active_ids', [])
    #     records = self.browse(active_ids)
    #     for record in records:
    #         _logger.info("Checking states...")
    #         if record.bill_created and record.linked_bill:
    #             _logger.info("Bill already exists...")
    #             return {
    #                 'type': 'ir.actions.act_window',
    #                 'name': 'Vendor Bill',
    #                 'res_model': 'account.move',
    #                 'view_mode': 'form',
    #                 'res_id': record.linked_bill.id,
    #                 'target': 'current',
    #             }
                
    #         if record.state == "completed":
    #             _logger.info("Job completed...")
                
    #             # 1. Checkear la diferencia de precio entre bill y el estimado. 
    #             # 2. hace el bill con la cuenta de EMRF Labor y matchear con el original y ajustar gasto de ser necesario
    #             return
            
    #         else:
    #             _logger.info("Creating bill...")
 
    #             bill = self.env['account.move'].sudo().create({
    #                 'move_type': 'in_invoice',
    #                 'partner_id': record.contractor_id.id,
    #                 'company_id': record.company.id,
    #                 'invoice_date': fields.Date.today(),
    #                 'invoice_date_due': record.estimated_job_co_date,
    #                 'state': 'draft',
    #                 'payment_reference': record.name,
    #                 # 'invoice_line_ids': (0, 0, {
    #                 #     'name': f'Job: {record.name}',
    #                 #     # 'product_id': line.product.id,
    #                 #     'account_id': self.env['account.account'].search([('company_id', '=', record.company.id)], limit=1).id,
    #                 #     'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
    #                 #     'quantity': 1,
    #                 #     'price_unit': record.estimated_cost
    #                 # })
    #             })
    #             record.linked_bill = bill.id
    #             record.bill_created = True
                
    #             return {
    #                 'type': 'ir.actions.act_window',
    #                 'name': 'Vendor Bill',
    #                 'res_model': 'account.move',
    #                 'view_mode': 'form',
    #                 'res_id': bill.id,
    #                 'target': 'current',
    #             }
    
    


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    is_synced_from_job = fields.Boolean(
        string="Synced from Job",
        default=False,
        help="Indicates if this attachment was synced from a contractor job."
    )