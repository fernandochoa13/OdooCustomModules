from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

import requests
from datetime import timedelta, datetime, date
import re

import logging
_logger = logging.getLogger(__name__)

ESCROW_ACCOUNT_NUMBER = '231222' # OLD NUMBER: 1815202
REPAIR_ACCOUNT_NUMBER = '6510008' # OLD NUMBER: 6510008
ACCOUNT_PAYABLE_NUMBER = '211000' # OLD NUMBER: 211000
LOAN_BETWEEN_RELATED_COMPANIES_NUMBER = '200401' # OLD NUMBER: 2000401

class PMSMaterials(models.Model):
    _name = "pms.materials"
    _description = "Material Orders"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Order Reference', compute="_compute_name", copy=False, readonly=True, index=True)
    property_id = fields.Many2one('pms.property', string='Property', index=True, tracking=True)
    property_name = fields.Char(related="property_id.name", store=True, readonly=True)
    county = fields.Many2one(related='property_id.county', store=True, readonly=True)
    property_owner = fields.Many2one(related='property_id.partner_id', store=True, readonly=True)
    house_model = fields.Many2one(related='property_id.house_model', store=True, readonly=True)
    on_hold = fields.Boolean(related='property_id.on_hold', string='On Hold') # redundant default
    own_third = fields.Selection(related='property_id.own_third', string='Own/Third Party') # redundant default
    reference = fields.Char(string='Reference')
    payment_terms = fields.Many2one('account.payment.term', string='Payment Terms', tracking=True, store=True)
    payment_terms_anticipated = fields.Boolean(related='payment_terms.anticipated_payment', string='Anticipated Payment', store=True)
    # payment terms boolean fix so it is not id CHECKED
    payment_method = fields.Text(string='Payment Method', readonly=True)
    payment_method_journal = fields.Many2one('account.journal', string='Payment Method Journal', readonly=True)
    project_phase = fields.Selection(selection=[
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
        ("coc", "COC"),
        ("completed", "Completed"),
        ], compute="_compute_project_phase", string="Project Phase", readonly=True, store=True)
    
    order_status = fields.Selection([
        ('not_ordered', 'Not Ordered'),
        ('wait_cust', 'Waiting for Customer Payment'),
        ('waiting_payment', 'Waiting Payment'),
        ('gave_payment', 'Gave Payment'),
        ('ordered', 'Ordered'),
        # ('waiting_conf', 'Waiting for Confirmation'),
        ('delivered', 'Delivered'),
        ('rejected', 'Order Rejected')
        ], string='Order Status', default='not_ordered', tracking=True)
    
    # STATUS DATES (IN ORDER)
    
    order_creation_date = fields.Datetime(string="Order Creation", readonly=False, compute="calc_order_creation", store=True, help='Date order created') # not_ordered
    def calc_order_creation(self):
        for record in self:
            record.order_creation_date = record.create_date
                
    order_request_date = fields.Datetime(string='Order Request Date', help='Date order set to "Waiting for Customer Payment"') # wait_cust
    waiting_payment_date = fields.Datetime(string="Payment Request Date", help='Date order set to "Waiting Payment"') # new waiting_payment
    payment_date = fields.Datetime(string='Payment Date', help='Date order set to "Gave Payment"') # gave_payment
    ordered_date = fields.Datetime(string='Ordered Date', help='Date order set to "Ordered"') # ordered
    estimated_delivery_date = fields.Datetime(string='Estimated Delivery Date', help='Estimated Date for Delivery')
    actual_delivery_date = fields.Datetime(string='Delivery Date', help='Date order set to "Delivered"') # delivered
    rejected_date = fields.Datetime(string='Rejected Date', readonly=True, help='Date order set to "Rejected"') # rejected
    
    # KPI1 :: Order Creation (wait_cust) --> Waiting Customer Payment / Waiting_Payment
    
    # not_ordered --> wait_cust (order_request_date - order_creation_date)
    
    created_to_waiting_cust = fields.Integer(group_operator='avg', default=False, string="Days from 'Creation Date' to 'Waiting Payment'", readonly=True, store=True, compute="calc_created_to_waiting_cust_days",
        help="""KPI1: Days between 'Order Creation Date' and 'Waiting for Customer Payment' or 'Waiting Customer Payment' fields.""")
    
    @api.depends('order_creation_date', 'order_request_date', 'waiting_payment_date', 'own_third')
    def calc_created_to_waiting_cust_days(self):
        for record in self:
            if record.own_third == 'third' and record.order_creation_date and record.order_request_date:
                record.created_to_waiting_cust = (record.order_request_date - record.order_creation_date).days
            elif record.own_third == 'own' and record.order_creation_date and record.waiting_payment_date:
                record.created_to_waiting_cust = (record.waiting_payment_date - record.order_creation_date).days
            else:
                record.created_to_waiting_cust = False
    
    # KPI2 :: Waiting_Payment --> Gave_Payment
    # (wait_cust) --> Waeiting_Payment / ordred
    
    wait_to_gave_pay = fields.Integer(group_operator='avg', default=False, string="Days from 'Payment Request' to 'Payment Date'", readonly=True, store=True, compute="calc_wait_to_gave_pay_days",
        help="""KPI2: Days between 'Order Request Date' and 'Ordered Date' fields.""")
    
    @api.depends('order_request_date', 'ordered_date', 'invoice_pay_date', 'waiting_payment_date', 'own_third')
    def calc_wait_to_gave_pay_days(self):
        for record in self:
            if record.own_third == 'third' and record.order_request_date and record.invoice_pay_date:
                record.wait_to_gave_pay = (record.invoice_pay_date - record.order_request_date.date()).days
            elif record.own_third == 'own' and record.waiting_payment_date and record.payment_date:
                record.wait_to_gave_pay = (record.payment_date - record.waiting_payment_date).days
            else:
                record.wait_to_gave_pay = False
            
    # KPI3: invoice_payment_date hasta ordered
    
    inv_pay_to_ordered = fields.Integer(group_operator='avg', default=False, readonly=True, string="Days from 'Invoice Payment Date' to 'Ordered Date'", store=True, compute="calc_inv_pay_to_ordered_days",
        help="""KPI3: Days between 'Invoice Payment Date' and 'Ordered Date' fields.""")
    
    @api.depends("invoice_pay_date", "ordered_date")
    def calc_inv_pay_to_ordered_days(self):
        for record in self:
            if record.own_third == 'third' and record.invoice_pay_date and record.ordered_date:
                invoice_pay_datetime = datetime.combine(record.invoice_pay_date, datetime.min.time())
                record.inv_pay_to_ordered = (record.ordered_date - invoice_pay_datetime).days
            elif record.own_third == 'own' and record.payment_date and record.ordered_date:
                invoice_pay_datetime = datetime.combine(record.payment_date, datetime.min.time())
                record.inv_pay_to_ordered = (record.ordered_date - invoice_pay_datetime).days
            else:
                record.inv_pay_to_ordered = False
    
    # cuando se cree la order, si se crea despues de las 12 el viernes, que lo registre como el proximo lunes a las 8:00 
    
    
    # KPI4 :: Ordered --> Delivered
    
    ordered_to_delivered = fields.Integer(group_operator='avg', default=False, readonly=True, string="Days from 'Ordered' to 'Delivered'", store=True, compute="delivered_to_ordered_calculator",
        help="""KPI4: Days between 'Ordered Date' and 'Actual Delivered Date' fields.""")
    
    @api.depends('actual_delivery_date', 'ordered_date')
    def delivered_to_ordered_calculator(self):
        for record in self:
            if record.actual_delivery_date and record.ordered_date:
                record.ordered_to_delivered = (record.actual_delivery_date.date() - record.ordered_date.date()).days
            else:
                record.ordered_to_delivered = False
    
    # # KPI4: waiting_for_customer_payment hasta invoice_payment_date
    
    # wait_to_inv_pay = fields.Integer(group_operator='avg', default=False, readonly=True, string="Days from 'Waiting Payment' to 'Invoice Payment Date'", store=True, compute="calc_wait_to_inv_pay_days",
    #     help="""KPI4: Days between 'Waiting Payment Date' and 'Invoice Payment Date' fields.""")
    
    # def calc_wait_to_inv_pay_days(self):
    #     for record in self:
    #         if record.invoice_pay_date and record.waiting_payment_date:
    #             invoice_pay_datetime = datetime.combine(record.invoice_pay_date, datetime.min.time()) #converts date to datetime at midnight.
    #             record.wait_to_inv_pay = (invoice_pay_datetime - record.waiting_payment_date).days
    #         else:
    #             record.wait_to_inv_pay = False
    
    # Invoice Metric :: Invoice Creation --> Invoice Paid
    invoice_creation = fields.Date(string='Invoice Creation', readonly=True)
    invoice_pay_date = fields.Date(string='Invoice Payment Date', readonly=True)
    invoice_days_to_paid = fields.Integer(default=None, string='Time to paid', readonly=True)
    
    # probar
    
    # chequear que ordered request date se llene cuando es manual y tambien por cmo
    # que waiting_payment y payment date se llenen, que nunca queden vacios
    # ordered date y delivery date se llenen cuando se cambia de estado
    
    # Other metrics
    time_to_ordered = fields.Integer(string='Time to Ordered', compute='_compute_time_to_ordered', store=True)
    time_to_rejected = fields.Integer(string='Time to Rejected', compute='_compute_time_to_rejected', store=True)
    time_to_delivered = fields.Integer(string='Time to Delivered', compute='_compute_time_to_delivered', store=True)
    
    provider = fields.Many2one('res.partner', string='Provider', tracking=True)
    has_bill = fields.Boolean(string='Bill', default=False)
    bill_id = fields.Integer(string='Bill ID', readonly=True)
    material_lines = fields.One2many('pms.materials.lines', 'material_order_id', string='Material Lines')
    total_order_amount = fields.Float(string='Total Order Amount', compute="_compute_total_order_amount", store=True, tracking=True)
    #material_id = fields.Many2one('daily.property.report', string='Material ID')
    project_manager = fields.Many2one(
        'hr.employee',
        string='Project Manager',
        related='property_id.projects.project_manager',
        store=True,
        readonly=True
    )

    superintendent = fields.Many2one(
        'hr.employee',
        string='Superintendent',
        related='property_id.projects.superintendent',
        store=True,
        readonly=True
    )

    zone_coordinator = fields.Many2one(
        'hr.employee',
        string='Zone Coordinator',
        related='property_id.projects.zone_coordinator',
        store=True,
        readonly=True
    )
    order_creator = fields.Many2one('hr.employee', string='Order Creator', tracking=True)
    rejections_count = fields.Integer(string='Rejections Count', default=0, readonly=True)
    rejection_note = fields.Text(string='Rejection Note', readonly=True)
    confirmed_by = fields.Many2one('hr.employee', string='Confirmed By', readonly=True)
    signed_by = fields.Binary(string='Signed By', readonly=True)
    linked_bill = fields.Many2one('account.move', string='Linked Bill', readonly=True)
    linked_payment = fields.Many2one('account.payment', string='Linked Payment', readonly=True)
    linked_invoice = fields.Many2one('account.move', string='Linked Invoice', readonly=False)
    paid_with_other_company = fields.Boolean(string='Paid with other Company', default=False)
    other_company = fields.Many2one('res.company', string='Other Company', required=False)
    other_company_journal = fields.Many2one('account.journal', string='Other Journal', required=False)

    main_journal_entry = fields.Many2one('account.move', string='Main Journal Entry', readonly=True)
    other_company_journal_entry = fields.Many2one('account.move', string='Other Company Journal Entry', readonly=True)

    company_third_party = fields.Many2one('res.company', string='Company', required=False)
    
    escrow_company = fields.Many2one(related='property_id.projects.escrow_company', string='Escrow Company', readonly=True)
    escrow_account = fields.Many2one('account.account', string='Escrow Account', compute='_compute_escrow_account', store=True, readonly=True)


    payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy')
    ], string='Payment State', compute='_compute_payment_status', readonly=True)
    
    invoice_payment_status = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy')
    ], string='Invoice Payment State', compute='_compute_payment_status', readonly=True)
    
    inv_payment_state = fields.Selection(related='linked_invoice.payment_state', string='Invoice Payment State', readonly=True, store=True)

    no_availability = fields.Boolean(string='No Availability from Previous Provider', default=False)
    provider_no_availability = fields.Many2one('res.partner', string='Previous Provider', readonly=True, store=True)
    # due_date = fields.Date(string='Due Date', compute="_compute_due_date", readonly=True)
    property_status = fields.Selection(related='property_id.status_property', string='Property Status', readonly=True)
    template_id = fields.Many2one('purchase.template', string='Template', readonly=True)
    linked_payment_request = fields.Integer(string='Linked Payment Request', readonly=True)
    credit_cards = fields.Many2one('credit.cards', string='Credit Card', readonly=True) # Unknown comodel_name 'credit.cards'.
    
    # link_to_new_bill = fields.Char(string='Link to New Bill', readonly=True)
    
    # CHECKS IF USER IS PURCHASE MANAGER, CONDITIONALLY ALLOWS EDITING OF SPECIAL_ORDER_APPROVED
    # ADDED VERIFICATION IN FUNCTIONS: DELIVERED, SET_DELIVERED AND ORDERED IF ORDER IS SPECIAL AND IF IT HAS APPROVAL
    # RAISES VALIDATION ERROR IF IT IS SPECIAL BUT DOESNT HAVE APPROVAL
    # SPECIAL_ORDER FIELD IS CONDITIONALLY RENDERED IF ORDER IS SPECIAL OR NOT
    
    # Special Order Fields
    
    special_order = fields.Boolean(string='Special Order', store=True, readonly=True)
    special_order_approved = fields.Boolean(string="Special Order Approved?", store=True, default=False)
    
    # 3rd Party Payment Fields
    
    third_party_payment = fields.Boolean(string='Third Party Payment', store=True, default=False)
    
    # Access Rights Fields
    
    is_purchase_manager = fields.Boolean(string="Purchase Manager?", compute="_compute_purchase_manager", readonly=True)
    is_purchase_analyst = fields.Boolean(string="Purchase Manager or Analyst?", compute="_compute_purchase_manager", readonly=True)
    
    def _compute_purchase_manager(self): 
        for record in self:
            record.is_purchase_manager = self.env.user.has_group('pms.group_account_purch_manager')
            record.is_purchase_analyst = self.env.user.has_group('pms.group_account_purch_analyst')
    
    # Re-Order Fields
    
    re_order_id = fields.One2many('pms.materials', 're_order_inv', string='Re-Orders', readonly=True)
    re_order_inv = fields.Many2one('pms.materials', string="inverse", readonly=True)
    
    followups = fields.One2many("material.order.follow.up", "material_id", string="Follow Ups")
    last_followup_message = fields.Text(string="Last Follow-up Message", compute='_compute_last_followup', store=True)
    last_followup_date = fields.Datetime(string="Last Follow-up Date", compute='_compute_last_followup', store=True)

    @api.depends('followups.date', 'followups.comment')
    def _compute_last_followup(self):
        for record in self:
            if record.followups:
                latest_followup = record.followups.sorted(key='date', reverse=True)[0]
                record.last_followup_message = latest_followup.comment
                record.last_followup_date = latest_followup.date
            else:
                record.last_followup_message = False
                record.last_followup_date = False
    
    
    def create_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Quotation',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'new',
            }
    
    @api.depends('escrow_company')
    def _compute_escrow_account(self):
        for record in self:
            record.escrow_account = False
            if record.escrow_company:
                escrow_account = self.env['account.account'].search([
                    ('code', '=', ESCROW_ACCOUNT_NUMBER),
                    ('company_id', '=', record.escrow_company.id)
                ], limit=1)
                if escrow_account:
                    record.escrow_account = escrow_account.id


    # Enviar sms & email when order is approved
    @api.onchange("special_order_approved")
    def notify_when_special_order_approved(self):
        _logger.info('notify_when_special_order_approved running...')
        if self.special_order_approved:  # Check if true
            
            emails = [
                "adan@adanordonezp.com"
            ]
            email_to = ','.join(emails)
            
            mail_values = {
                    'subject': f'Special Order Approved: {self.name}',
                    'body_html': f"""
                        <html>
                            <head>
                            <meta charset="UTF-8">
                                <title>Special Order Approved!</title>
                            </head>
                            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f8f8; padding: 20px; margin: 0;">
                                <div style="background-color: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); max-width: 600px; margin: 20px auto;">
                                    <h1 style="color: #007bff; font-size: 28px; margin-bottom: 20px; text-align: center;">Special Order Approved! 🎉</h1>
                                    <p style="margin-bottom: 15px;">The following special order has been approved:</p>
                                    <p><span style="font-weight: bold; color: #28a745;">{self.name}</span></p>
                                </div>
                            </body>
                        </html>
                    """,
                    'email_to': email_to
                }
            self.env['mail.mail'].sudo().create(mail_values).send()

            
            # Send sms to 
            
            access_token = self.env['sms.silvamedia'].search([], limit=1).access_token
            message = f'Special Order "{self.name}" has been approved.'
            contact_id = "NN9TQ5PNiBCAfOspmBFx"
            numbers = [
                "+14707901135"
            ]
            
            # location_id = self.env['sms.silvamedia'].search([], limit=1).location_id
            for number in numbers:
                _logger.info('Attempting to send SMS to %s', number)
                try:
                    new_sms = requests.post("https://services.leadconnectorhq.com/conversations/messages",
                        json={
                                'contactId': contact_id,
                                'message': message,
                                'toNumber': number,
                                'type': 'SMS'
                            },
                        headers={
                                'Authorization': f'Bearer {access_token}',
                                'Version': '2021-07-28',
                                'Content-Type': 'application/json',
                                'Accept': 'application/json'
                            })
                    
                    print(new_sms.json())
                    new_sms.raise_for_status()
                    _logger.info('Successfully sent SMS to %s', number)
                    
                    return {
                        'type': 'ir.actions.client', 'tag': 'display_notification',
                        'params': {'message': message, 'type': 'info', 'sticky': False}
                    }
                    
                except requests.exceptions.RequestException as e:
                    error_message = str(e)
                    truncated_message = error_message[:85] + "..." if len(error_message) > 80 else error_message                
                    _logger.info('Failed to send SMS to %s', number)
                    _logger.info('SMS Error: %s', str(e))
                    self.env['update.owner.call.day'].simple_notification("warning", 'Failed to send SMS', truncated_message, True)
                    return
            
            # purchase_manager_group = self.env.ref('pms.group_account_purch_manager')

            # purchase_manager_emails = self.env['res.users'].search([
            #     ('groups_id', 'in', purchase_manager_group.id),
            #     ('partner_id.email', '!=', False)
            # ]).mapped('partner_id.email')

            # if purchase_manager_emails:
            #     mail_values = {
            #         'subject': f'Special Order #{self.name} Approved',
            #         'body_html': f'Special Order "{self.name}" has been approved.',
            #     }

            #     for employee_email in purchase_manager_emails:
            #         mail_values['email_to'] = employee_email
            #         self.env['mail.mail'].sudo().create(mail_values).send()

            #     # Send SMS
            #     message = f'Special Order "{self.name}" has been approved.'
            #     self._send_sms_messages(message)
            # else:
            #     _logger.warning(f"No purchase managers found or no emails configured for special order {self.name}")
            
            # Send email to adan@adanordonezp.com

    # ORDER_STATUS CHANGE HERE
    def set_delivered(self):
        # if not self.env.user.has_group('pms.group_account_purch_manager'):
        #     raise ValidationError(_("Orders can only be set to delivered by a Purchase Manager."))
        if self.special_order and not self.special_order_approved:
            raise ValidationError(_("Special orders require approval by a Purchase Manager."))

        self.actual_delivery_date = fields.Datetime.now() # added
        self.order_status = 'delivered'
        self.delivered_to_ordered_calculator()
        
    
    def set_delivered_on_bulk(self):
        for record in self:
            if record.order_status == 'delivered':
                continue
            if record.order_status not in ['gave_payment', 'ordered']:
                notes = f'''
                    <div style="background-color: #FFDDDD; color: #8B0000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #FF8080">
                        <b>Automatic 'Set to Delivered' Failed:</b><br>
                        <i>Order {record.name} was not in 'Ordered' state.</i>
                    </div>
                '''
                record.message_post(body=notes)
                continue
            else:
                record.write({
                    'actual_delivery_date': fields.Datetime.now(),
                    'order_status': 'delivered',
                })
                record.delivered_to_ordered_calculator()
                notes = f'''
                    <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                        <b>The following Material Order has been set to 'Delivered' on bulk:</b><br>
                        <i>{record.name}</i>
                    </div>
                '''
                record.message_post(body=notes)


    def open_order(self):
        view = self.env.ref('pms.pms_materials_view_form')
        return {
                'name': 'Material Orders',
                'type': 'ir.actions.act_window',
            'view_mode': 'form',
                'res_model': 'pms.materials',
                'res_id': self.id,
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'current',
        }
        
    def redo_order(self):
        new_ref = 'Re-order: ' + self.reference
        new_order = self.create({
            'order_creator': self.order_creator.id,
            'property_id': self.property_id.id,
            'property_status': self.property_status,
            'county': self.county.id,
            'property_owner': self.property_owner.id,
            'project_manager': self.project_manager.id,
            'zone_coordinator': self.zone_coordinator.id,
            'superintendent': self.superintendent.id,
            'house_model': self.house_model.id,
            'on_hold': self.on_hold,
            'own_third': self.own_third,
            'project_phase': self.project_phase,
            'provider': self.provider.id,
            'reference': new_ref if self.reference else 'Re-order: no reference',
            'payment_terms_anticipated': self.payment_terms_anticipated,
            'order_request_date': fields.Date.today(),
            'payment_method': self.payment_method,
            'payment_method_journal': self.payment_method_journal.id,
            'special_order': True,
            'special_order_approved': False
        })
        if new_order:
            self.re_order_id = [(4, new_order.id, 0)]
            notes = f'''
                    <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                        <b>Re-Order from Order:</b><br>
                        <i>{self.name}</i>
                    </div>
                '''
            new_order.message_post(body=notes)
            view = self.env.ref('pms.pms_materials_view_form')
            return {
                    'name': 'Material Orders',
                    'type': 'ir.actions.act_window',
            'view_mode': 'form',
                    'res_model': 'pms.materials',
                    'res_id': new_order.id,
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'current',
            }
        else:
            self.env['update.owner.call.day'].simple_notification("warning", False, 'There was an error creating the re-order.', False)                                                            
        
# on_hold_wizard = self.env.ref('pms.view_on_hold_wizard_form')
#         return {
#                 'name': 'On Hold History Wizard',
#                 'type': 'ir.actions.act_window',
#                 'view_type': 'form',
#                 'view_mode': 'form',
#                 'res_model': 'on.hold.wizard',
#                 'views': [(on_hold_wizard.id, 'form')],
#                 'view_id': on_hold_wizard.id,
#                 'target': 'new',
#                 'context': {'default_property_id': self.id}
#                 }


    @api.depends("property_id", "estimated_delivery_date", "reference")
    def _compute_name(self):
        for record in self:
            name = []
            if record.property_id: name.append(record.property_id.name)
            if record.estimated_delivery_date: name.append(str(record.estimated_delivery_date))
            if record.reference: name.append(record.reference)
            record.name = " | ".join(name) if name else ""
                
                
    def view_payment_request(self):
        if not self.linked_payment_request:
            raise UserError(_('There is no payment request for this order.'))
        return {
            'name': 'Credit Card Programmed Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'cc.programmed.payment',
            'view_mode': 'form',
            'res_id': self.linked_payment_request,
        }

    def no_availability_button(self):
        return {
        'type': 'ir.actions.act_window',
        'name': 'No Availability Wizard',    
        'res_model': 'no.availability.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {'default_material_order_id': self.id,
                    'default_provider_no_availability': self.provider.id} 
}

    @api.depends('ordered_date', 'order_request_date')
    def _compute_time_to_ordered(self):
        for record in self:
            if record.ordered_date and record.order_request_date:
                record.time_to_ordered = (record.ordered_date - record.order_request_date).days
                if record.time_to_ordered < 0:
                    record.time_to_ordered = 0
            else:
                record.time_to_ordered = 0

    @api.depends('rejected_date', 'ordered_date')
    def _compute_time_to_rejected(self):
        for record in self:
            if record.rejected_date and record.ordered_date:
                record.time_to_rejected = (record.rejected_date - record.ordered_date).days
                if record.time_to_rejected < 0:
                    record.time_to_rejected = 0
            else:
                record.time_to_rejected = 0


    # Duplicated, ordered -> delivered already exists, potentially remove computed field if not in use

    @api.depends('actual_delivery_date', 'ordered_date')
    def _compute_time_to_delivered(self):
        for record in self:
            if record.actual_delivery_date and record.ordered_date:
                record.time_to_delivered = (record.actual_delivery_date - record.ordered_date).days
                if record.time_to_delivered < 0:
                    record.time_to_delivered = 0
            else:
                record.time_to_delivered = None
                
                


    @api.depends('linked_bill', 'linked_invoice') # NEEDS TESTING
    def _compute_payment_status(self):
        _logger.info("Running _compute_payment_status")
        for record in self:
            if record.linked_bill:
                bill = self.env['account.move'].sudo().browse(record.linked_bill.id)
                record.payment_status = bill.payment_state
            else:
                record.payment_status = False  
                
            if record.linked_invoice:
                invoice = record.linked_invoice
                record.invoice_payment_status = invoice.payment_state
                record.invoice_creation = record.linked_invoice.date
                
                matched_invoice_line = invoice.line_ids.filtered(lambda line: line.matching_number)
                
                if matched_invoice_line:
                    match_number = matched_invoice_line[0].matching_number
                    matched_move_line = self.env['account.move.line'].search([
                            ('matching_number', '=', match_number),
                            ('account_id.account_type', '=', 'asset_receivable'),
                            ('company_id', '=', invoice.company_id.id)
                        ], limit=1)
                    if matched_move_line:
                        record.invoice_pay_date = matched_move_line.move_id.date
                        record.invoice_days_to_paid = (matched_move_line.move_id.date - record.linked_invoice.date).days
                        
                    else:
                        _logger.info('No matched move line found for invoice %s with matching number %s', invoice.name, match_number)
                        record.invoice_days_to_paid = False
                else:
                    _logger.info('No matched invoice line found for invoice %s', invoice.name)
                    record.invoice_days_to_paid = False
            else:
                _logger.info('No linked invoice found for material order %s', record.name)
                record.invoice_payment_status = False
                record.invoice_days_to_paid = False

                # if record.invoice_payment_status == 'not_paid':
             
                #     record.invoice_creation = record.linked_invoice.date
                #     record.invoice_days_to_paid = False
                    
                # elif record.invoice_payment_status in ('paid', 'in_payment'):

                #     record.invoice_days_to_paid = (fields.Date.today() - record.invoice_creation.date()).days
                    
                
                # record.linked_invoice.date would be the ideal invoice creation date to use
                # Buscar reemplazar fields.Date.today() con el date de account.payment, para mayor consistencia 
                
                
    # @api.depends('linked_bill')
    # def _compute_due_date(self):
    #     for record in self:
    #         if record.linked_bill:
    #             bill = self.env['account.move'].browse(record.linked_bill.id)
    #             record.due_date = bill.invoice_date_due
    #         else:
    #             record.due_date = False 



    @api.depends("property_id")
    def _compute_project_phase(self):
        for record in self:
            projects = record.env["pms.projects"].search([("address", "=", record.property_id.id)]).ids
            if projects:
                project = record.env["pms.projects"].browse(projects[0])
                record.project_phase = project.status_construction
            else:
                record.project_phase = "pending"

    @api.depends("material_lines")
    def _compute_total_order_amount(self):
        for record in self:
            record.total_order_amount = sum(line.total for line in record.material_lines)



    # Create Invoice

        # En que empresa se va a registrar CHECKED
        # Corregir Proveedor CHECKED
        # En empresa owner de la propiedad. CHECKED
        # Si propiedad cerrada reparaciones sino no normal. Repair 6510008 - bill lines CHECKED


        # En caso q la compania no sea propia, determinar Escrow o tercero. 
        # Escrow = Crear bill con cuenta escrow money in custody - hacer el bill en la escrow company CHECKED
        # Tercero = Crear Invoice al tercero - ponerle un link con la order - y orden se queda en waiting for payment


        # Si viene de gave payment
        # Crear el bill
        # Crear el pago
        # Si se paga con otra empresa
        # 2 journal entry ademas del bill:
        # 1. En empresa de la propiedad: DEBIT: Accounts Payable CREDIT: Loan between related companies con partner la otra empresa
        # Matchea el bill con el pago
    
    create_a_bill = fields.Boolean(string='Create a Bill', default="True", help="If checked, a bill will be created for this order when the 'Create Bill' button is pressed. If unchecked, no bill will be created.")
        
    def create_bill(self): # NEEDS TESTING
        _logger.info("Running create_bill function")
        
        if not self.create_a_bill:
            return self.env['update.owner.call.day'].simple_notification("warning", False, 'Create bill off, skipping bill creation.', False)
        if self.has_bill == True:
            raise UserError(_('Bill already created for this order.'))
        elif self.property_id.on_hold == True and self.order_status == 'not_ordered':
            raise UserError(_('The selected property is on hold. You cannot create a bill for this property.'))
        else:
            company = self.env['res.company'].search([('partner_id', '=', self.property_id.partner_id.id)], limit=1).id
            repair_account = self.env['account.account'].search(['&',('code', '=', REPAIR_ACCOUNT_NUMBER), ('company_id', '=', company)], limit=1).id
            # if self.special_order == True:
            #     bill = self.env['account.move'].sudo().create({
            #             'move_type': 'in_invoice',
            #             'partner_id': self.provider.id,
            #             'company_id': company,
            #             'invoice_date': fields.Date.today(),
            #             'state': 'draft',
            #             'payment_reference': self.name,
            #         })

            #     self.linked_bill = bill.id
            #     self.has_bill = True
            if not self.payment_terms or not self.payment_terms.line_ids:
                raise ValidationError(_("Can't create a bill without a valid payment term."))
            else:
                due_date = fields.Date.today() + timedelta(days=self.payment_terms.line_ids[0].days)
            if not company and self.paid_with_other_company == False:
                project_custodial = self.env['pms.projects'].search([('address', '=', self.property_id.id), ('custodial_money', '=', True)], limit=1).escrow_company.id
                escrow_account = self.env['account.account'].search(['&',('code', '=', ESCROW_ACCOUNT_NUMBER), ('company_id', '=', project_custodial)], limit=1).id
                if project_custodial:
                    invoice_lines_esc = [(0, 0, {
                        'name': line.product.name,
                        'product_id': line.product.id,
                        'account_id': escrow_account,
                        'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                        'quantity': line.quantity,
                        'price_unit': line.amount,
                    }) for line in self.material_lines]

                    bill = self.env['account.move'].sudo().create({
                    'move_type': 'in_invoice',
                    'partner_id': self.provider.id,
                    'company_id': project_custodial,
                    'invoice_date': fields.Date.today(),
                    'invoice_date_due': due_date,
                    'state': 'draft',
                    'payment_reference': self.name,
                    'invoice_line_ids': invoice_lines_esc,
                })
                    bill.linked_material_order = self.id
                    bill.action_post()
                    self.linked_bill = bill.id
                    self.has_bill = True
                
                elif not project_custodial:
                    create_company_wizard = self.env.ref('pms.company_selector_wizard_form')
                    return {
                        'name': 'Company Selector Wizard',
                        'type': 'ir.actions.act_window',
            'view_mode': 'form',
                        'res_model': 'company.selector.wizard',
                        'views': [(create_company_wizard.id, 'form')],
                        'view_id': create_company_wizard.id,
                        'target': 'new',
                        'context': {'active_id': self.id}
                    }
                
            elif self.paid_with_other_company == True:
                self.create_records_paid_with_other_company()
            else:
                if self.property_id.residential_unit_closure == True and self.create_a_bill:
                    invoice_lines_rep = [(0, 0, {
                        'name': line.product.name,
                        'product_id': line.product.id,
                        'account_id': repair_account,
                        'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                        'quantity': line.quantity,
                        'price_unit': line.amount,
                    }) for line in self.material_lines]
                    
                    bill = self.env['account.move'].sudo().create({
                        'move_type': 'in_invoice',
                        'partner_id': self.provider.id,
                        'company_id': company,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': due_date,
                        'state': 'draft',
                        'payment_reference': self.name,
                        'invoice_line_ids': invoice_lines_rep if invoice_lines_rep else [],
                    })

                    bill.linked_material_order = self.id
                    bill.action_post()
                    self.linked_bill = bill.id
                    self.has_bill = True


                else:
                    invoice_lines = [(0, 0, {
                        'name': line.product.name,
                        'product_id': line.product.id,
                        'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                        'quantity': line.quantity,
                        'price_unit': line.amount,
                    }) for line in self.material_lines]
                    if self.create_a_bill:
                        bill = self.env['account.move'].sudo().create({
                            'move_type': 'in_invoice',
                            'partner_id': self.provider.id,
                            'company_id': company,
                            'invoice_date': fields.Date.today(),
                            'invoice_date_due': due_date,
                            'state': 'draft',
                            'payment_reference': self.name,
                            'invoice_line_ids': invoice_lines,
                        })

                        bill.linked_material_order = self.id
                        bill.action_post()
                        self.linked_bill = bill.id
                        self.has_bill = True

                
    def write(self, vals):
        if 'order_status' in vals and vals['order_status'] in ['rejected', 'delivered']:
            old_status = self.order_status

            result = super(PMSMaterials, self).write(vals)

            self.send_email_gave_pay()

            return result

        return super(PMSMaterials, self).write(vals)
    
    # def send_status_change_message_gave_pay(self):
    #     odoobot_partner = self.env.ref('base.partner_root')

    #     property_users = set() 

    #     purchase_manager_group = self.env.ref('pms.group_account_purch_manager')

    #     purchase_manager_users = self.env['res.users'].search([
    #         ('groups_id', 'in', purchase_manager_group.id)
    #     ])

    #     for user in purchase_manager_users:
    #         property_users.add(user.partner_id)

    #     if not property_users:
    #         raise UserError('No users tied to the property to send a message to.')

    #     message_content = f"The status of the material order {self.name} has changed to {self.order_status}."

    #     for user_partner in property_users:
    #         direct_message_channel = self.env['mail.channel'].search([
    #             ('channel_partner_ids', 'in', [odoobot_partner.id]),  
    #             ('channel_partner_ids', 'in', [user_partner.id]),    
    #             ('channel_type', '=', 'chat') 
    #         ], limit=1)

    #         if not direct_message_channel:
    #             direct_message_channel = self.env['mail.channel'].sudo().create({
    #                 'channel_partner_ids': [(4, odoobot_partner.id), (4, user_partner.id)],
    #                 'channel_type': 'chat',
    #                 'name': f"Direct Message with {user_partner.name}"
    #             })

    #         direct_message_channel.message_post(
    #             body=message_content,
    #             message_type='comment',
    #             subtype_xmlid='mail.mt_comment',
    #             author_id=odoobot_partner.id 
    #         )

    #     return True
    
    def send_email_wait_pay(self): # NEEDS TESTING
        property_users = set()

        purchase_manager_group = self.env.ref('pms.group_account_purch_manager')
        payment_manager_group = self.env.ref('pms.group_account_payment_manager')

        purchase_manager_users = self.env['res.users'].search([
            ('groups_id', 'in', purchase_manager_group.id)
        ])

        payment_manager_users = self.env['res.users'].search([
            ('groups_id', 'in', payment_manager_group.id)
        ])

        for user in purchase_manager_users:
            if user.partner_id.email:
                property_users.add(user.partner_id.email)

        for user in payment_manager_users:
            if user.partner_id.email:
                property_users.add(user.partner_id.email)

        if property_users:
            print(property_users)

            for employee_email in property_users:
                message_content = f"The status of the material order {self.name} has changed to Waiting for Payments."
                self.env['mail.mail'].sudo().create({
                    'subject': f'Order #{self.name} Status Change',
                    'body_html': message_content,
                    'email_to': employee_email,
                }).send()
        else:
            pass

    def send_email_gave_pay(self): # NEEDS TESTING
        property_users = set()

        purchase_manager_group = self.env.ref('pms.group_account_purch_manager')

        purchase_manager_users = self.env['res.users'].search([
            ('groups_id', 'in', purchase_manager_group.id)
        ])

        for user in purchase_manager_users:
            if user.partner_id.email:
                property_users.add(user.partner_id.email)

        if property_users:
            for employee_email in property_users:
                message_content = f"The status of the material order {self.name} has changed to Gave Payment."
                self.env['mail.mail'].sudo().create({
                    'subject': f'Order #{self.name} Status Change',
                    'body_html': message_content,
                    'email_to': employee_email,
                }).send()
        else:
            pass
                
    # def send_status_change_message_wait_pay(self):
    #     odoobot_partner = self.env.ref('base.partner_root')

    #     property_users = set() 

    #     purchase_manager_group = self.env.ref('pms.group_account_purch_manager')
    #     payment_manager_group = self.env.ref('pms.group_account_payment_manager')

    #     purchase_manager_users = self.env['res.users'].search([
    #         ('groups_id', 'in', purchase_manager_group.id)
    #     ])

    #     payment_manager_users = self.env['res.users'].search([
    #         ('groups_id', 'in', payment_manager_group.id)
    #     ])

    #     for user in purchase_manager_users:
    #         property_users.add(user.partner_id)

    #     for user in payment_manager_users:
    #         property_users.add(user.partner_id)

    #     if not property_users:
    #         raise UserError('No users tied to the property to send a message to.')

    #     message_content = f"The status of the material order {self.name} has changed to {self.order_status}."

    #     for user_partner in property_users:
    #         direct_message_channel = self.env['mail.channel'].search([
    #             ('channel_partner_ids', 'in', [odoobot_partner.id]),  
    #             ('channel_partner_ids', 'in', [user_partner.id]),    
    #             ('channel_type', '=', 'chat') 
    #         ], limit=1)

    #         if not direct_message_channel:
    #             direct_message_channel = self.env['mail.channel'].sudo().create({
    #                 'channel_partner_ids': [(4, odoobot_partner.id), (4, user_partner.id)],
    #                 'channel_type': 'chat',
    #                 'name': f"Direct Message with {user_partner.name}"
    #             })

    #         direct_message_channel.message_post(
    #             body=message_content,
    #             message_type='comment',
    #             subtype_xmlid='mail.mt_comment',
    #             author_id=odoobot_partner.id 
    #         )

    #     return True

                
    def create_invoice(self):
        _logger.info("Running create_invoice function")
        
        if not self.payment_terms or not self.payment_terms.line_ids:
            raise UserError(_("Can't create an invoice without a payment term."))
        else:
            payment_term = self.env['account.payment.term'].search([("material_payment", '=', True)], limit=1)

            due_date = fields.Date.today() + timedelta(days=self.payment_terms.line_ids[0].days)
        invoice_lines = [(0, 0, {
            'name': line.subproduct.name,
            'product_id': line.product.id,
            'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
            'quantity': line.quantity,
            'price_unit': line.amount,
        }) for line in self.material_lines]

        invoice = self.env['account.move'].sudo().create({
            'move_type': 'out_invoice',
            'partner_id': self.property_owner.id,
            'company_id': self.company_third_party.id,
            'contractor': self.provider.id,
            'invoice_date': fields.Date.today(),
            'linked_material_order': self.id,
            'invoice_date_due': due_date,
            'state': 'draft',
            'payment_reference': self.name,
            'invoice_line_ids': invoice_lines,
            'invoice_payment_term_id': payment_term.id if payment_term else False,
        })

        self.linked_invoice = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice', 
            'res_model': 'account.move',
            'res_id': self.linked_invoice.id,
            'view_mode': 'form',
            'target': 'current', 
        }

    def create_records_paid_with_other_company(self):
        _logger.info("Running create_records_paid_with_other_company function")
        
        main_company = self.env['res.company'].search([('partner_id', '=', self.property_id.partner_id.id)], limit=1).id
        project_custodial = self.env['pms.projects'].search([('address', '=', self.property_id.id), ('custodial_money', '=', True)], limit=1).escrow_company.id
        escrow_account = self.env['account.account'].search(['&',('code', '=', ESCROW_ACCOUNT_NUMBER), ('company_id', '=', project_custodial)], limit=1).id
        repair_account = self.env['account.account'].search(['&',('code', '=', REPAIR_ACCOUNT_NUMBER), ('company_id', '=', main_company)], limit=1).id
        if not self.payment_terms or not self.payment_terms.line_ids:
            raise UserError(_("Can't create records without a payment term for the order."))
        else:
            due_date = fields.Date.today() + timedelta(days=self.payment_terms.line_ids[0].days)
        if project_custodial:
            invoice_lines = [(0, 0, {
                            'name': line.product.name,
                            'product_id': line.product.id,
                            'account_id': escrow_account,
                            'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                            'quantity': line.quantity,
                            'price_unit': line.amount,
                        }) for line in self.material_lines]
            main_company = project_custodial
        elif self.property_id.residential_unit_closure == True:
            invoice_lines = [(0, 0, {
                            'name': line.product.name,
                            'product_id': line.product.id,
                            'account_id': repair_account,
                            'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                            'quantity': line.quantity,
                            'price_unit': line.amount,
                        }) for line in self.material_lines]
        else:
            invoice_lines = [(0, 0, {
                            'name': line.product.name,
                            'product_id': line.product.id,
                            'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                            'quantity': line.quantity,
                            'price_unit': line.amount,
                        }) for line in self.material_lines]

        main_journal_entry_lines = [
            (0, 0, {
                'name': 'Account Payable',
                'account_id': self.env['account.account'].search([('code', '=', ACCOUNT_PAYABLE_NUMBER), ('company_id', '=', main_company)], limit=1).id,
                'debit': self.total_order_amount,
                'partner_id': self.provider.id,
                'credit': 0.0,
            }),
            (0, 0, {
                'name': 'Loan between related companies',
                'account_id': self.env['account.account'].search([('code', '=', LOAN_BETWEEN_RELATED_COMPANIES_NUMBER), ('company_id', '=', main_company)], limit=1).id,
                'credit': self.total_order_amount,
                'debit': 0.0,
                'partner_id': self.other_company.partner_id.id,
            }),
        ]

        main_journal_entry = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'partner_id': self.provider.id,
            'company_id': main_company,
            'date': fields.Date.today(),
            'line_ids': main_journal_entry_lines
        })

        other_company_journal_entry_lines = [
            (0, 0, {
                'name': 'Loan between related companies',
                'account_id': self.env['account.account'].search([('code', '=', LOAN_BETWEEN_RELATED_COMPANIES_NUMBER), ('company_id', '=', self.other_company.id)], limit=1).id,
                'debit': self.total_order_amount,
                'credit': 0.0,
                'partner_id': self.property_owner.id,
            }),
            (0, 0, {
                'name': 'Outstanding Payments',
                'partner_id': self.provider.id,
                'account_id': self.other_company_journal.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                'credit': self.total_order_amount,
                'debit': 0.0,
            }),
        ]

        other_company_journal_entry = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'partner_id': self.provider.id,
            'company_id': self.other_company.id,
            'date': fields.Date.today(),
            'journal_id': self.other_company_journal.id,
            'line_ids': other_company_journal_entry_lines
        })
        if self.create_a_bill:
            bill = self.env['account.move'].sudo().create({
                        'move_type': 'in_invoice',
                        'partner_id': self.provider.id,
                        'company_id': main_company,
                        'invoice_date': fields.Date.today(),
                        'invoice_date_due': due_date,
                        'state': 'draft',
                        'payment_reference': self.name,
                        'invoice_line_ids': invoice_lines,
                    })

            bill.linked_material_order = self.id
            bill.action_post()
            self.linked_bill = bill.id
            self.has_bill = True
        main_journal_entry.action_post()
        other_company_journal_entry.action_post()

        self.main_journal_entry = main_journal_entry.id
        self.other_company_journal_entry = other_company_journal_entry.id

        # self.show_bill()


    def create_payment(self): # NEEDS TESTING
        company = self.env['res.company'].search([('partner_id', '=', self.property_id.partner_id.id)], limit=1).id
        company_escrow = self.env['pms.projects'].search(['&',('address', '=', self.property_id.id), ('custodial_money', '=', True)], limit=1).escrow_company.id
        if not company:
            if company_escrow:
                payment = self.env['account.payment'].sudo().create({
                    'partner_id': self.provider.id,
                    'company_id': company_escrow,
                    'invoice_date': fields.Date.today(),
                    'state': 'draft',
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'amount': self.total_order_amount,
                    'ref': self.payment_method or self.name,
                })
            else:
                create_company_wizard = self.env.ref('pms.company_selector_wizard_form')
                return {
                    'name': 'Company Selector Wizard',
                    'type': 'ir.actions.act_window',
            'view_mode': 'form',
                    'res_model': 'company.selector.wizard',
                    'views': [(create_company_wizard.id, 'form')],
                    'view_id': create_company_wizard.id,
                    'target': 'new',
                    'context': {'active_id': self.id}
                }
        else:
            payment = self.env['account.payment'].sudo().create({
                    'partner_id': self.provider.id,
                    'company_id': company,
                    'invoice_date': fields.Date.today(),
                    'state': 'draft',
                    'journal_id': self.payment_method_journal.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'amount': self.total_order_amount,
                    'ref': self.payment_method or self.name,
                })
        payment.action_post()
        self.payment_date = fields.Datetime.today() # datetime
        self.linked_payment = payment.id

    def view_bill(self):
        if self.linked_bill == False:
            raise UserError(_('No Bill found'))
        else:
            return {
            'type': 'ir.actions.act_window',
            'name': ('account.view_move_form'),
            'res_model': 'account.move',
            'res_id': self.linked_bill.id,
            'view_mode': 'form'}



    def set_ordered_date(self):
        """
        Sets the ordered_date to Monday 8:00 AM if the current time 
        is between Friday and Monday cutoff hours.

        Returns: datetime.datetime: The adjusted ordered_date.
        """
        # CUTOFF HOURS CONTROLLERs
        friday_cutoff_hour = 12
        monday_cutoff_hour = 6

        # DATE AND CUTOFF HOUR CALCULATORS
        now = datetime.now()
        friday = now + timedelta((4 - now.weekday()) % 7)
        friday_cutoff = friday.replace(hour=friday_cutoff_hour, minute=0, second=0, microsecond=0)

        monday = now + timedelta((0 - now.weekday()) % 7)
        monday_cutoff = monday.replace(hour=monday_cutoff_hour, minute=0, second=0, microsecond=0)
        monday_8am = monday.replace(hour=8, minute=0, second=0, microsecond=0)

        if friday_cutoff <= now < monday_cutoff:
            return monday_8am
        else:
            return now

#############################################################################################################################################################################################################

    # Enviar notificacion SMS y EMAIL cuando pase a ordered

    def ordered(self): # NEEDS TESTING
        _logger.info("Running ordered function")
        # Checks if its a special order and if it has been approved
        
        if self.special_order and not self.special_order_approved:
            raise ValidationError(_("Special orders require approval by a Purchase Manager."))

        # Checks if the order has a payment term assigned
        
        if not self.payment_terms and not self.payment_terms.line_ids:
            raise UserError(_("Can't process an order without a payment term assigned."))

        # Checks if the property is on hold

        if self.property_id.on_hold == True and self.order_status == 'not_ordered':
            raise UserError(_('The selected property is on hold. You cannot process a material order for this property.'))
        
        is_special_escrow = False
        special_escrows = [
            'CFL REHABBERS LLC',
        ]
        
        company = self.env['res.company'].search([('partner_id', '=', self.property_id.partner_id.id)], limit=1).id
        project_custodial = self.env['pms.projects'].search([('address', '=', self.property_id.id), ('custodial_money', '=', True)], limit=1).escrow_company.id
        
        is_special_escrow_search = self.env['res.company'].search([
            ('id', '=', project_custodial),
            ('name', 'in', special_escrows)
        ])
        
        if is_special_escrow_search.id:
            is_special_escrow = is_special_escrow_search.id
            _logger.info(f"Special Escrow: " + str(is_special_escrow))
        else:
            _logger.info(f"No Special Escrow")
            
        # Checks if it has company, if its not escrow
        # and if the property_owner is different from the company partner_id

        if self.property_owner.id != self.env.company.partner_id.id and not project_custodial and company: 
            create_bill_wizard = self.env.ref('pms.material_order_bill_wizard_form')
            # Added Create Request Payment 
            return {
                    'name': 'Material Order Bill Wizard',
                    'type': 'ir.actions.act_window',
            'view_mode': 'form',
                    'res_model': 'material.order.bill.wizard',
                    'views': [(create_bill_wizard.id, 'form')],
                    'view_id': create_bill_wizard.id,
                    'target': 'new',
                    'context': {'default_property_id': self.property_id.id,
                                'default_invoice_origin': self.name,
                                'default_material_lines': self.material_lines.ids,
                                'default_partner_id': self.property_owner.id,
                                'default_order_id': self.id,
                                'order_status': self.order_status
                                }
                    }

        # Checks if the order has no company (own, third, escrow)

        if not company and not project_custodial and not self.company_third_party and not self.third_party_payment:
            create_company_wizard = self.env.ref('pms.company_selector_wizard_form')

            return {
                'name': 'Company Selector Wizard',
                'type': 'ir.actions.act_window',
            'view_mode': 'form',
                'res_model': 'company.selector.wizard',
                'views': [(create_company_wizard.id, 'form')],
                'view_id': create_company_wizard.id,
                'target': 'new',
                'context': {'active_id': self.id}
            }

        # checks if the property is third party

            # if third party payment
            
        if self.third_party_payment:
            domain = [
                ('analytic_accounts', 'ilike', self.property_name),
                ('contractor', '=', self.provider.id),
                ('state', '!=', 'cancel')
            ]
            linked_invoice = self.env['account.move'].search(domain, limit=1)

            if linked_invoice:
                _logger.info("Set ordered here 10")
                self.write({
                    'linked_invoice': linked_invoice.id,
                    'order_status': 'wait_cust',
                    'order_request_date': fields.Datetime.now(),
                    'created_to_waiting_cust': (fields.Datetime.now() - self.create_date).days if self.create_date else False,
                })
                return 

            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "No linked invoice found. Operation cancelled.",
                        'type': 'danger',
                        'sticky': False
                    }
                } 

        if self.company_third_party:

            # if company is special escrow
            
            if is_special_escrow:
                if self.order_status == 'wait_cust':
                    self.create_request_payment(company=is_special_escrow)
                    self.create_bill_after_invoice(is_special_escrow=is_special_escrow)
                    # ORDER_STATUS CHANGE HERE
                    self.order_status = 'ordered'
                    _logger.info("Set ordered here 1")
                    self.ordered_date = self.set_ordered_date()
                    self.delivered_to_ordered_calculator()
                    
                else: 
                    create_company_wizard = self.env.ref('pms.company_selector_wizard_form')
                    return {
                        'name': 'Company Selector Wizard',
                        'type': 'ir.actions.act_window',
            'view_mode': 'form',
                        'res_model': 'company.selector.wizard',
                        'views': [(create_company_wizard.id, 'form')],
                        'view_id': create_company_wizard.id,
                        'target': 'new',
                        'context': {'active_id': self.id}
                    }
            
            # If gave_payment but not paid with other company
            
            elif self.order_status == 'gave_payment' and not self.paid_with_other_company:
                self.create_payment_after_invoice()
                self.create_bill_after_invoice()
                
                domain = [
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('reconciled', '=', False),
                ]
                bill = self.env['account.move'].browse(self.linked_bill.id)
                payment = self.env['account.payment'].browse(self.linked_payment.id)
                bill_line = bill.line_ids.filtered_domain(domain)
                payment_line = payment.line_ids.filtered_domain(domain)
                
                for account in payment_line.account_id:
                    (payment_line + bill_line)\
                        .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                        .reconcile()
                # ORDER_STATUS CHANGE HERE
                self.order_status = 'ordered'
                _logger.info("Set ordered here 2")
                self.delivered_to_ordered_calculator()
                self.ordered_date = self.set_ordered_date()

            # If gave_payment but paid with other company

            elif self.order_status == 'gave_payment' and self.paid_with_other_company:
                self.create_bill_after_invoice()
                domain = [
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('reconciled', '=', False),
                ]
                bill = self.env['account.move'].browse(self.linked_bill.id)
                payment = self.env['account.move'].browse(self.main_journal_entry.id)
                bill_line = bill.line_ids.filtered_domain(domain)
                payment_line = payment.line_ids.filtered_domain(domain)
                
                for account in payment_line.account_id:
                    (payment_line + bill_line)\
                        .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                        .reconcile()
                # ORDER_STATUS CHANGE HERE
                self.order_status = 'ordered'
                _logger.info("Set ordered here 3")
                self.ordered_date = self.set_ordered_date()
                self.delivered_to_ordered_calculator()

            # If not gave_payment
            
            else:
                # Added Create Request Payment 
                self.create_request_payment(company=self.env.company.id)
                self.create_bill_after_invoice()
                # ORDER_STATUS CHANGE HERE
                self.order_status = 'ordered'
                _logger.info("Set ordered here 4")
                self.ordered_date = self.set_ordered_date()
                self.delivered_to_ordered_calculator()
         
        # if not third party 
                
        else:
            if self.order_status == 'gave_payment' and not self.paid_with_other_company:
                self.create_payment()
                self.create_bill()
                domain = [
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('reconciled', '=', False),
                ]
                bill = self.env['account.move'].browse(self.linked_bill.id)
                payment = self.env['account.payment'].browse(self.linked_payment.id)
                bill_line = bill.line_ids.filtered_domain(domain)
                payment_line = payment.line_ids.filtered_domain(domain)
                
                for account in payment_line.account_id:
                    (payment_line + bill_line)\
                        .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                        .reconcile()
                # ORDER_STATUS CHANGE HERE
                self.order_status = 'ordered'
                _logger.info("Set ordered here 5")
                self.ordered_date = self.set_ordered_date()
                self.delivered_to_ordered_calculator()
            elif self.order_status == 'gave_payment' and self.paid_with_other_company == True:
                self.create_bill()
                domain = [
                    ('parent_state', '=', 'posted'),
                    ('account_type', 'in', ('asset_receivable', 'liability_payable')),
                    ('reconciled', '=', False),
                ]
                bill = self.env['account.move'].browse(self.linked_bill.id)
                payment = self.env['account.move'].browse(self.main_journal_entry.id)
                bill_line = bill.line_ids.filtered_domain(domain)
                payment_line = payment.line_ids.filtered_domain(domain)
                
                for account in payment_line.account_id:
                    (payment_line + bill_line)\
                        .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                        .reconcile()
                # ORDER_STATUS CHANGE HERE
                self.order_status = 'ordered'
                _logger.info("Set ordered here 6")
                self.ordered_date = self.set_ordered_date()
                self.delivered_to_ordered_calculator()
            else:
                # Added Create Request Payment 
                self.create_request_payment(company=self.env.company.id)
                self.create_bill()
                # ORDER_STATUS CHANGE HERE
                self.order_status = 'ordered'
                _logger.info("Set ordered here 7")
                self.ordered_date = self.set_ordered_date()
                self.delivered_to_ordered_calculator()
                
        message = 'Order %s on property %s has been ordered.' % (self.name, self.property_id.name)
        self._send_sms_messages(message)

        if self.linked_bill and self.create_a_bill:
            _logger.info("linked_bill running here")
            record = self.linked_bill.id
            if self.linked_payment_request:
                self.env['cc.programmed.payment'].browse(self.linked_payment_request).sudo().write({'bill_id': self.linked_bill.id,
                                                                                              'state': 'paid'})
            return {
                'type': 'ir.actions.act_window',
                'name': 'Bill',
                'res_model': 'account.move',
                'res_id': record,
                'view_mode': 'form',
                'views': [(self.env.ref('account.view_move_form').id, 'form')],
                'target': 'current',
            }
            
        elif self.linked_invoice:
            # ORDER_STATUS CHANGE HERE
            self.order_status = 'wait_cust'
            self.order_request_date = fields.Datetime.now() # added
            if self.order_creation_date and self.create_date:
                self.created_to_waiting_cust = (self.order_request_date - self.create_date).days
            self.delivered_to_ordered_calculator()

#######################################################################################################

    def create_request_payment(self, company=False):
        order_id = self.id
        provider = self.provider.id
        payment_date = self.payment_date
        requested_by = self.order_creator.id
        reference = self.name
        amount = self.total_order_amount
        new_payment_request = self.env['cc.programmed.payment'].sudo().create({
            'requested_by': requested_by,
            'provider': provider,
            'amount': amount,
            'company': company,
            'request_date': fields.Date.today(),
            'payment_date': payment_date,
            'concept': reference,
            'properties':  [(6, 0, [self.property_id.id])],
            'material_order': order_id,
            'request_type': 'material',
            'bill_id': self.linked_bill.id,
            'has_bill': True,
        }) 
        self.linked_payment_request = new_payment_request.id

        
        
        #      record = self.env['cc.programmed.payment'].sudo().create({
        #     'bill_id': self.id,
        #     'has_bill': True,
        # })
    
    def create_payment_after_invoice(self):
        payment = self.env['account.payment'].sudo().create({
            'partner_id': self.provider.id,
            'company_id': self.company_third_party.id,
            'invoice_date': fields.Date.today(),
            'state': 'draft',
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'amount': self.total_order_amount,
            'ref': self.payment_method or self.name,
        })
        payment.action_post()
        # self.payment_date = fields.Datetime.today() # datetime # resetting payment_date after its already been previously set
        self.linked_payment = payment.id
    
    def create_bill_after_invoice(self, is_special_escrow=False): # NEEDS TESTING
        _logger.info("Running create_bill_after_invoice function")
        
        if not self.create_a_bill:
            self.env['update.owner.call.day'].simple_notification("warning", False, 'Create bill is disabled, if you wish to create a bill, please reenable.', False)
        if not self.payment_terms or not self.payment_terms.line_ids:
            raise UserError(_("Can't create a bill without a payment term."))
        else:
            due_date = fields.Date.today() + timedelta(days=self.payment_terms.line_ids[0].days)
        if self.paid_with_other_company == False:

            company = is_special_escrow if is_special_escrow else self.company_third_party.id            
            
            invoice_lines = [(0, 0, {
                'name': line.product.name,
                'product_id': line.product.id,
                'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                'quantity': line.quantity,
                'price_unit': line.amount,
            }) for line in self.material_lines]
            if self.create_a_bill:
                bill = self.env['account.move'].sudo().create({
                    'move_type': 'in_invoice',
                    'partner_id': self.provider.id,
                    'company_id': company,
                    'invoice_date': fields.Date.today(),
                    'invoice_date_due': due_date,
                    'state': 'draft',
                    'payment_reference': self.name,
                    'invoice_line_ids': invoice_lines,
                })
                bill.linked_material_order = self.id
                bill.action_post()
                self.linked_bill = bill.id
            
        elif self.paid_with_other_company == True:
            main_journal_entry_lines = [
            (0, 0, {
                'name': 'Account Payable',
                'account_id': self.env['account.account'].search([('code', '=', ACCOUNT_PAYABLE_NUMBER), ('company_id', '=', self.company_third_party.id)], limit=1).id,
                'debit': self.total_order_amount,
                'partner_id': self.provider.id,
                'credit': 0.0,
            }),
            (0, 0, {
                'name': 'Loan between related companies',
                'account_id': self.env['account.account'].search([('code', '=', LOAN_BETWEEN_RELATED_COMPANIES_NUMBER), ('company_id', '=', self.company_third_party.id)], limit=1).id,
                'credit': self.total_order_amount,
                'debit': 0.0,
                'partner_id': self.other_company.partner_id.id,
            }),
        ]

            main_journal_entry = self.env['account.move'].sudo().create({
                'move_type': 'entry',
                'partner_id': self.provider.id,
                'company_id': self.company_third_party.id,
                'date': fields.Date.today(),
                'line_ids': main_journal_entry_lines
            })

            other_company_journal_entry_lines = [
                (0, 0, {
                    'name': 'Loan between related companies',
                    'account_id': self.env['account.account'].search([('code', '=', LOAN_BETWEEN_RELATED_COMPANIES_NUMBER), ('company_id', '=', self.other_company.id)], limit=1).id,
                    'debit': self.total_order_amount,
                    'credit': 0.0,
                    'partner_id': self.property_owner.id,
                }),
                (0, 0, {
                    'name': 'Outstanding Payments',
                    'partner_id': self.provider.id,
                    'account_id': self.other_company_journal.outbound_payment_method_line_ids.filtered_domain([('payment_method_id', '=', 'Manual')]).payment_account_id.id,
                    'credit': self.total_order_amount,
                    'debit': 0.0,
                }),
            ]

            other_company_journal_entry = self.env['account.move'].sudo().create({
                'move_type': 'entry',
                'partner_id': self.provider.id,
                'company_id': self.other_company.id,
                'date': fields.Date.today(),
                'journal_id': self.other_company_journal.id,
                'line_ids': other_company_journal_entry_lines
            })
            
            invoice_lines = [(0, 0, {
                'name': line.product.name,
                'product_id': line.product.id,
                'analytic_distribution': {str(self.property_id.analytical_account.id): 100.0},
                'quantity': line.quantity,
                'price_unit': line.amount,
            }) for line in self.material_lines]
            if self.create_a_bill:
                bill = self.env['account.move'].sudo().create({
                    'move_type': 'in_invoice',
                    'partner_id': self.provider.id,
                    'company_id': self.company_third_party.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_date_due': due_date,
                    'state': 'draft',
                    'payment_reference': self.name,
                    'invoice_line_ids': invoice_lines,
                })
                bill.linked_material_order = self.id
                bill.action_post()
                self.linked_bill = bill.id
                
            main_journal_entry.action_post()
            other_company_journal_entry.action_post()

            self.main_journal_entry = main_journal_entry.id
            self.other_company_journal_entry = other_company_journal_entry.id


    def request_payment(self):
        # ORDER_STATUS CHANGE HERE
        self.order_status = 'waiting_payment'
        # Set waiting_payment_date here
        self.waiting_payment_date = fields.Datetime.now()


        self.delivered_to_ordered_calculator()
        self.send_email_wait_pay()
        company = self.env['res.company'].search([('partner_id', '=', self.property_id.partner_id.id)], limit=1).id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Request CC Payment Validation',
            'res_model': 'request.cc.payment.validation',
            'view_mode': 'form',
            'target': 'new',
            'context': {'property_owner': self.property_owner.id,
                        'company': company,
                        'amount': self.total_order_amount,
                        'payment_date': self.payment_date,
                        'reference': self.reference,
                        'property_id': self.property_id.id,
                        'provider': self.provider.id,
                        'order_id': self.id
                        }
        }

    def gave_payment(self):
        # Open wizard to give payment details CHECKED
        # Action to use multiple at the same time CHECKED
        self.ensure_one()
        if self.order_status == 'delivered':
            return self.env['update.owner.call.day'].simple_notification("warning", False, 'This material order has already been delivered.', False)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Payment Wizard',
            'res_model': 'material.order.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.ids,
                        'property_owner': self.property_owner.id}
        }



###########################################################################################################################################################################################################


 # Nueva funcion para manejar solo emails

    def _send_email_to(self, email_addresses, html_content): # NEEDS TESTING
        if not email_addresses:
            return {
                'type': 'ir.actions.act_window',
                'name': 'No Email Wizard',
                'res_model': 'no.email.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'order_id': self.id}
            }
        else:
            email_to = ','.join(email_addresses)
            mail_values = {
                'subject': f'Order #{self.name} is waiting for confirmation',
                'body_html': html_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
            
    # Nueva funcion para enviar solo sms 
    

    def _send_sms_messages(self, message): # NEEDS TESTING
        self.ensure_one()
        access_token = self.env['sms.silvamedia'].search([], limit=1).access_token
        location_id = self.env['sms.silvamedia'].search([], limit=1).location_id
        _logger.info('Phone Numbers: %s', self.ids)
        _logger.info('Message: %s', message)

        partner_list = []
        
        if self.superintendent and self.superintendent.related_contact_ids:
            superintendent = self.env["res.partner"].browse(self.superintendent.related_contact_ids.ids[0])
            if self.superintendent not in partner_list:
                partner_list.append(superintendent)
                _logger.info('Superintendent appended.')
            else:
                _logger.info('Superintendent already in list.')
        else:
            _logger.info('No Superintendent.')
            
        if self.zone_coordinator and self.zone_coordinator.related_contact_ids:
            zone_coordinator = self.env["res.partner"].browse(self.zone_coordinator.related_contact_ids.ids[0])
            if zone_coordinator not in partner_list: 
                partner_list.append(zone_coordinator)
                _logger.info('Zone Coordinator appended.')
            else:
                _logger.info('Zone Coordinator already in list.')
        else:
            _logger.info('No Zone Coordinator.')

        if self.project_manager and self.project_manager.related_contact_ids:
            project_manager = self.env["res.partner"].browse(self.project_manager.related_contact_ids.ids[0])
            if project_manager not in partner_list:
                partner_list.append(project_manager)
                _logger.info('Project Manager appended.')
            else:
                _logger.info('Project Manager already in list.')
        else:
            _logger.info('No Project Manager.')

        if self.order_creator and self.order_creator.related_contact_ids:
            order_creator = self.env["res.partner"].browse(self.order_creator.related_contact_ids.ids[0])
            if order_creator not in partner_list:
                partner_list.append(order_creator)
                _logger.info('Order Creator appended.')
            else:
                _logger.info('Order Creator already in list.')
        else:
            _logger.info('No Order Creator.')

        purchase_manager_group = self.env.ref('pms.group_account_purch_manager')
        purchase_manager_users = self.env['res.users'].search([
            ('groups_id', 'in', purchase_manager_group.id)
        ])
        for user in purchase_manager_users:
            if user.partner_id not in partner_list:
                partner_list.append(user.partner_id)
                _logger.info('User appended.')
            else:
                _logger.info('User already in list.')    
        
        
        _logger.info('Partners: %s', partner_list)
        if partner_list == []:
            return _logger.info('No partners were found.')
        else:
            for partner in partner_list:
                _logger.info('Partner: %s', partner)

                if not partner.phone:
                    _logger.info('%s has no phone number.', partner.name)
                    self.env['update.owner.call.day'].simple_notification("warning", False, '%s has no phone number.' % partner.name, False)
                    continue
                
                if not re.match(r'^\+1\d{10}$', partner.phone):
                    _logger.info('%s\'s phone number doesn\'t have a valid format.', partner.name)
                    self.env['update.owner.call.day'].simple_notification("warning", False, '%s\'s phone number doesn\'t have a valid format.' % partner.name, False)                  
                    continue

                if not partner.contact_id:
                    try:
                        new_user = requests.post(
                            "https://services.leadconnectorhq.com/contacts/",
                                json={
                                        'firstName': partner.name,
                                        'lastName': partner.name,
                                        'name': f'{partner.name}',
                                        'email': partner.email,
                                        'locationId': location_id,
                                        'phone': partner.phone,
                                    },
                                headers={
                                        'Authorization': f'Bearer {access_token}',
                                        'Version': '2021-07-28',
                                        'Content-Type': 'application/json',
                                        'Accept': 'application/json'
                                    })
                        print(new_user.json())
                        new_user.raise_for_status()
                        self.env['res.partner'].browse(partner.partner_id).sudo().write({'contact_id': new_user.contact_id})
                        return new_user.json().get('contact').get('id')
                    except requests.exceptions.RequestException as e:
                        _logger.info('Failed to create contact for %s. Error: %s' % (partner.name, e))
                        self.env['update.owner.call.day'].simple_notification("warning", False, 'Failed to create contact for %s.' % partner.name, False)                                       
                        continue            
            
                # Send SMS 
                _logger.info('Sending SMS to %s',partner.phone)
                try:
                    new_sms = requests.post("https://services.leadconnectorhq.com/conversations/messages",
                                            json={
                                                    'contactId': partner.contact_id,
                                                    'message': message,
                                                    'toNumber': partner.phone,
                                                    'type': 'SMS'
                                                },
                                            headers={
                                                    'Authorization': f'Bearer {access_token}',
                                                    'Version': '2021-07-28',
                                                    'Content-Type': 'application/json',
                                                    'Accept': 'application/json'
                                                })
                    print(new_sms.json())
                    new_sms.raise_for_status()
                except requests.exceptions.RequestException as e:
                    _logger.info('Failed to send SMS to %s', partner.name)
                    self.env['update.owner.call.day'].simple_notification("warning", False, 'Failed to send SMS to %s' % partner.name, False)                                                            
                    continue 

    # CREATE MATERIAL ORDER FUNCTIONS

    def go_back(self):
        redirect = {
            'type': 'ir.actions.act_url',
            'url': '/web',
            'target': 'self',
        }
        return redirect
    
    def view_orders(self):
        employee_id = self._context.get('default_order_creator')
        redirect = {
                'name': 'Material Orders',
                'type': 'ir.actions.act_window',
                'res_model': 'pms.materials',
                'views': [
                    [self.env.ref('create_material_orders.material_orders_view_kanban').id, 'kanban'],
                    [self.env.ref('create_material_orders.material_orders_view_tree').id, 'tree'], 
                    [self.env.ref('create_material_orders.material_orders_view_calendar').id, 'calendar'], 
                ],
                'target': 'fullscreen',
                # 'domain': [('order_creator', '=', employee_id)],
                'context': {
                    'default_order_creator': employee_id,
                    # 'search_default_waiting_conf': 1
                    }
            }
        return redirect

    # Funcion para cerrar ordenes automaticamente despues de x dias
    # after_x_days es ingresado en el scheduled action: "Automatically Close Orders After X Days"

    # def update_order_status(self, after_x_days):
    #     today = fields.Datetime.now()
    #     count = 0
    #     orders = self.env['pms.materials'].search([('order_status', '=', 'ordered')])
    #     order_count = len(orders)
    #     for order in orders:
    #         if (today - order.actual_delivery_date).days > after_x_days:
    #             count += 1
    #             order.order_status = 'delivered'
    #             order.actual_delivery_date = today
    #             order.confirmed_by = self.env.user.id
                
    #     self.env['update.owner.call.day'].simple_notification("warning", False, '%s out of %s orders automatically confirmed after %s days.' 
    #                                                           % (count, order_count, after_x_days), False)
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'message': '%s out of %s orders automatically confirmed after %s days.' % (count, order_count, after_x_days),
        #         'type': 'info',
        #         'sticky': False,
        #         }
        #     } 
        

    # Enviar notifiacion EMAIL cuando pase a waiting_conf
    
    # def waiting_for_conf(self):
    # self.order_status = 'waiting_conf'
    #     self.actual_delivery_date = fields.Datetime.now()

    #     html_content = f'''
    #         <h2 style="font-family:Arial;">Order #{self.name} on property {self.property_id} is waiting for confirmation.</h2>
    #         <p style="font-family:Arial;">The order is waiting to be confirmed.</p>
    #     ''' 
    #     email_addresses = []
        
    #     if self.project_manager.work_email:
    #         email_addresses.append(self.project_manager.work_email)
    #     if self.superintendent.work_email:
    #         email_addresses.append(self.superintendent.work_email)
    #     if self.zone_coordinator.work_email:
    #         email_addresses.append(self.zone_coordinator.work_email)
    #     if self.order_creator.work_email:
    #         email_addresses.append(self.order_creator.work_email)

    #     purchase_manager_group = self.env.ref('pms.group_account_purch_manager')
    #     purchase_manager_users = self.env['res.users'].search([
    #         ('groups_id', 'in', purchase_manager_group.id)
    #     ])

    #     for user in purchase_manager_users:
    #         if user.partner_id.email: 
    #             email_addresses.append(user.partner_id.email)

    #     email_addresses = list(filter(None, email_addresses))
            
    #     self._send_email_to(email_addresses, html_content)

    #     # SMS Notification cuando pase a waiting_conf


    #     message = 'Order %s on property %s is waiting to be confirmed.' % (self.name, self.property_id.name)
        
    #     self._send_sms_messages(message)


##################################################################################################################################################################################################################################################################################################################

    def delivered(self):
        if self.special_order and not self.special_order_approved:
            raise ValidationError(_("Special orders require approval by a Purchase Manager."))
        # ORDER_STATUS CHANGE HERE
        self.order_status = 'delivered'
        self.delivered_to_ordered_calculator()

    def return_to_not_ordered(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Not Ordered Wizard',
            'res_model': 'not.ordered.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id}
        }

    def open_action(self):
        action_view = self.env.ref('create_material_orders.material_orders_view_form')
        return {
            'name': 'Material Orders Form',
            'type': 'ir.actions.act_window',
            'res_model': 'pms.materials',
            'view_mode': 'form',
            'view_id': action_view.id,
            'res_id': self.id,
            'target': 'current',
        }


    def confirm_order(self):
        employee_id = self._context.get('default_employee')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm Orders Wizard',
            'res_model': 'confirm.orders.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'order_id': self.id,
                        'material_lines': self.material_lines.ids,
                        'default_employee': employee_id}
        }
    
    def send_message_team(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Message to Team',
            'res_model': 'send.order.message.wizard',
            'view_mode': 'form',
            'target': 'new',
            # 'context': {'order_id': self.id}
            'context': {
                'active_id': self.id,
                'model': self._name,
            }
        }

    def view_teams_message(self):
        pass

class NoEmailWizard(models.TransientModel):
    _name = 'no.email.wizard'
    _description = 'No Email Wizard'


    def confirm_no_email(self):
        order = self._context.get('order_id')
        material_order = self.env['pms.materials'].browse(order)
        material_order.order_status = 'ordered'


class PMSMaterialsline(models.Model):
    _name = "pms.materials.lines"
    _description = "Material Orders Lines"

    material_order_id = fields.Many2one('pms.materials', string='Material Order')
    product = fields.Many2one('product.product', string='Product')
    subproduct = fields.Many2one('product.subproduct', string='Subproduct')
    unit_measure = fields.Char(string='Unit of Measure')
    quantity = fields.Integer(string='Quantity')
    amount = fields.Float(string='Amount')
    total = fields.Float(string='Total', compute="_compute_total", store=True)

    @api.depends("quantity", "amount")
    def _compute_total(self):
        for record in self:
            record.total = record.quantity * record.amount


class MaterialOrderPaymentWizard(models.TransientModel):
    _name = 'material.order.payment.wizard'
    _description = 'Material Order Payment Wizard'

    property_owner_company = fields.Many2one('res.company', string='Company', required=False)
    payment_method_journal = fields.Many2one('account.journal', string='Payment Method Journal (optional)', required=False, domain="[('type', 'in', ['cash', 'bank']), ('company_id', '=', property_owner_company)]")

    paid_with_other_company = fields.Boolean(string='Paid with other Company', default=False)

    other_company = fields.Many2one('res.company', string='Other Company', required=False)
    payment_method_journal_oc = fields.Many2one('account.journal', string='Payment Method Journal', required=False, domain="[('company_id', '=', other_company), ('type', 'in', ['cash', 'bank'])]")

    payment_method = fields.Text(string='Payment Method', required=True)

    @api.model
    def default_get(self, fields):
        res = super(MaterialOrderPaymentWizard, self).default_get(fields)

        property_owner = self.env.context.get('property_owner')
        company = self.env['res.company'].search([('partner_id', '=', property_owner)], limit=1).id


        if company:
            res.update({
                'property_owner_company': company
            })
        else:
            res.update({
                'property_owner_company': self.env.company.id
            })

        return res

    # def confirm_payment(self):
    #     orders = self._context.get('active_id')
    #     for order in orders:
    #         material_order = self.env['pms.materials'].browse(order)
    #         material_order.payment_method = self.payment_method
    #         if self.payment_method_journal:
    #             material_order.payment_method_journal = self.payment_method_journal.id
    #             material_order.order_status = 'gave_payment'
    #             material_order.payment_date = fields.Datetime.now() # added
    #             material_order.send_email_gave_pay()
    #         elif self.paid_with_other_company == True and self.payment_method_journal_oc:
    #             material_order.order_status = 'gave_payment'
    #             material_order.payment_date = fields.Datetime.now() # added
    #             material_order.payment_method_journal = self.payment_method_journal_oc.id
    #             material_order.paid_with_other_company = self.paid_with_other_company   
    #             material_order.other_company = self.other_company.id
    #             material_order.other_company_journal = self.payment_method_journal_oc.id
    #             material_order.send_email_gave_pay()

    def confirm_payment(self): # optimized for single write
        orders = self._context.get('active_ids', [])
        for order_id in orders:
            material_order = self.env['pms.materials'].browse(order_id)
            vals = {
                'payment_method': self.payment_method,
                'order_status': 'gave_payment',
                'payment_date': fields.Datetime.now(),
            }

            if self.payment_method_journal:
                vals['payment_method_journal'] = self.payment_method_journal.id
            elif self.paid_with_other_company and self.payment_method_journal_oc:
                vals['payment_method_journal'] = self.payment_method_journal_oc.id
                vals['paid_with_other_company'] = self.paid_with_other_company
                vals['other_company'] = self.other_company.id
                vals['other_company_journal'] = self.payment_method_journal_oc.id

            material_order.write(vals)
            material_order.send_email_gave_pay()

class CompanyWizard(models.TransientModel):
    _name = 'company.selector.wizard'
    _description = 'Company Selector Wizard'

    company = fields.Many2one('res.company', string='Company', required=True)

    def confirm_selection(self):
        order_id = self._context.get('active_id')
        material_order = self.env['pms.materials'].browse(order_id)
        vals = {
            'company_third_party': self.company.id,
            'order_status': 'wait_cust',
            'order_request_date': fields.Datetime.now(),  # added
        }
        if material_order and material_order.create_date:
            vals['created_to_waiting_cust'] = (fields.Datetime.now() - material_order.create_date).days
        else:
            vals['created_to_waiting_cust'] = 0

        material_order.write(vals)
        
        material_order.create_invoice()
        inv_id = material_order.linked_invoice.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice', 
            'res_model': 'account.move',
            'res_id': inv_id ,
            'view_mode': 'form',
            'target': 'current',
        }
    
class NotOrderedWizard(models.TransientModel):
    _name = 'not.ordered.wizard'
    _description = 'Not Ordered Wizard'

    def continue_not_ordered(self): # optimized to one write
        _logger.info("Running continue_not_ordered function")
        
        order_id = self._context.get('active_id')
        material_order = self.env['pms.materials'].browse(order_id)
        vals = {
            'ordered_date': False,
            'time_to_ordered': False,
            'has_bill': False,
            'payment_method': False,
            'payment_method_journal': False,
            'paid_with_other_company': False,
            'other_company': False,
            'other_company_journal': False,
            'payment_date': False,
            'order_request_date': False, # added
            'waiting_payment_date': False, # added
            'actual_delivery_date': False,
            'payment_terms': False,
            'company_third_party': False,
            'linked_bill': False,
            'linked_payment': False,
            'linked_invoice': False,
            'main_journal_entry': False,
            'other_company_journal_entry': False,
            'order_status': 'not_ordered',
            'invoice_creation': False,
            'invoice_pay_date': False,
            'invoice_days_to_paid': False,
            'rejection_note': False,
            'confirmed_by': False,
            'signed_by': False,
        }
        
        bill = self.env['account.move'].browse(material_order.linked_bill.id)
        if bill:
            bill.button_draft()
            bill.button_cancel()
        payment = self.env['account.payment'].browse(material_order.linked_payment.id)
        if payment:
            payment.action_draft()
            payment.action_cancel()
        invoice = self.env['account.move'].browse(material_order.linked_invoice.id)
        if invoice:
            invoice.button_draft()
            invoice.button_cancel()
        if material_order.main_journal_entry:
            main_journal_entry = self.env['account.move'].browse(material_order.main_journal_entry.id)
            main_journal_entry.button_draft()
            main_journal_entry.button_cancel()
        if material_order.other_company_journal_entry:
            other_company_journal_entry = self.env['account.move'].browse(material_order.other_company_journal_entry.id)
            other_company_journal_entry.button_draft()
            other_company_journal_entry.button_cancel()
        pay_request = self.env['cc.programmed.payment'].browse(material_order.linked_payment_request)
        if pay_request:
            if pay_request.state == 'paid':
                pass
            else:
                pay_request.unlink()
                vals['linked_payment_request'] = False
                
        material_order.write(vals)


##########################################################################################################################################################################################

# Ejecutar funcion en modulo?

class RequestCCPaymentValidation(models.Model):
    _name = 'request.cc.payment.validation'
    _description = 'Request CC Payment Validation'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)

    def confirm_payment_request(self):
        order_id = self._context.get('order_id')
        provider = self._context.get('provider')
        company = self._context.get('company')
        payment_date = self._context.get('payment_date')
        reference = self._context.get('reference')
        property_id = self._context.get('property_id')
        amount = self._context.get('amount')
        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])
        if pin_verification:
            record = self.env['cc.programmed.payment'].sudo().create({
            'requested_by': self.employee_id.id,
            'provider': provider,
            'amount': amount,
            'company': company if company else "",
            'request_date': fields.Date.today(),
            'payment_date': payment_date,
            'concept': reference,
            'properties': [(6, 0, [property_id])],
            'material_order': order_id,
            'request_type': 'material',
        }) 

            self.env['pms.materials'].browse(order_id).linked_payment_request = record.id

            return {
                'name': 'Payment Request',
                'type': 'ir.actions.act_window',
                'res_model': 'cc.programmed.payment',
                'res_id': record.id,
                'view_mode': 'form',
                'target': 'current',
            }   
        else:
            raise ValidationError(_('Invalid Employee PIN'))