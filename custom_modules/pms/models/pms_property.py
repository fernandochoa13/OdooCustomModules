from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.fields import Command

from datetime import datetime, date

import logging
_logger = logging.getLogger(__name__)

class pms_property(models.Model):
    _name = "pms.property"
    _description = "Table for properties"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    # === General Property Description === #
    name = fields.Char(compute="_property_full_address", store=True)
    parcel_id = fields.Char(string="Parcel ID", required=True)
    address = fields.Char(required=True, string="Property Address")
    country_id = fields.Many2one('res.country', required=True, string='Country')
    state_ids = fields.Many2one('res.country.state', required=True, string='Federal States', domain="[('country_id', '=?', country_id)]")
    city = fields.Many2one('pms.cities', string='City', required=True)
    zipcode = fields.Integer(help="This the zip code of the property", string="Property Zip Code", required=True)
    county = fields.Many2one('pms.county', string="County")
    description = fields.Char()
    partner_id = fields.Many2one("res.partner", string="Owner of property", tracking=True)
    partner_tax_id = fields.Char(related='partner_id.vat', string="Owner Tax ID", readonly=True)
    nunits = fields.Integer(string="Number of Units", required=True, default=1)
    projects = fields.One2many("pms.projects", "address", string="Projects")
    house_model = fields.Many2one("pms.housemodels", string="House Model")
    available = fields.Boolean(string="Available For Sale", default=True, tracking=True)
    available_for_rent = fields.Boolean(string="Available For Rent", default=False, tracking=True)
    superintendent = fields.Many2one("hr.employee", compute="_compute_superintendent", string="Superintendent", store=True)
    # ordered_materials = fields.One2many("pms.materials", "property_id", domain=[("order_status", "=", "ordered")], string="")
    # not_ordered_materials = fields.One2many("pms.materials", "property_id", domain=[("order_status", "=", "not_ordered")], string="")
    vacant = fields.Boolean(string="Vacant", default=False)
    arv = fields.Float(string="ARV")
    permit_number = fields.Char(string="Permit Number")

    # === ON HOLD FIELDS === #

    on_hold = fields.Boolean(string="Is property On Hold?", readonly=True, default=False, tracking=True)
    hold_by_owner = fields.Boolean(string="Hold by Owner", default=False, tracking=True, store=True, readonly=True)
    date_last_set_on_hold = fields.Date(string="Date Set On Hold", readonly=True, store=True)
    days_on_hold = fields.Integer(string="Days on Hold", compute='_compute_days_on_hold', store=True, readonly=True, tracking=True)
    @api.depends('date_last_set_on_hold')
    def _compute_days_on_hold(self):
        for record in self:
            if record.date_last_set_on_hold:
                delta = date.today() - record.date_last_set_on_hold
                record.days_on_hold = delta.days
            else:
                record.days_on_hold = 0
    
    
    exclude_on_hold = fields.Boolean(string="Exclude from On Hold", default=False, tracking=True)
    is_on_hold_manager = fields.Boolean(string="Is On Hold Manager", compute='_compute_is_on_hold_manager', store=False)

    def _compute_is_on_hold_manager(self):
        for record in self:
            record.is_on_hold_manager = self.env.user.has_group('pms.group_account_onhold_manager')
            
            
    # === Insurance Description === #
    property_insurance = fields.One2many("pms.insuranceline", "properties_associates", string="Insurance Policies")
    flood_zone = fields.Boolean(string="Flood Zone", default=False, tracking=True)
    # === Units Description === #
    units = fields.One2many("pms.units", "property_address", string="Units")

    # === Accounting Tag === #
    analytical_plan = fields.Many2one("account.analytic.plan", string="Analytical Plan", required=True)
    analytical_account = fields.Many2one("account.analytic.account", string="Analytical Account", index=True)

    # === Budget Id === #
    budget_ids = fields.Many2one("crossovered.budget")


    # === Passed to Residential Unit === #
    residential_unit_closure = fields.Boolean(string="Residential Unit", tracking=True)
    residential_unit_date = fields.Date(string="Residential Unit Date", tracking=True)

    # === Currency fields === #
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Accounting Company',
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True
    )

    # === Utilities Fields === #
    utilities_accounts = fields.One2many("pms.utility", "name", string="Utilities Connected")

    # === Financial Details === #
    transaction_history = fields.One2many("pms.transactions", "property_address")

    # === Status Property === #
    status_property = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('construction', "Construction"),
            ('coc', "COC"),
            ('rented', "Rented"),
            ('sold', "Sold"),
            ('repair', "Repair"),
        ],
        string="Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='draft')
    
    loans = fields.One2many("pms.loans", "property_address")
    
    own_third = fields.Selection(selection=[("own", "Own"), ("third", "Third")], compute='_compute_own_third', store=True)

    custodial_money = fields.Boolean(related="projects.custodial_money", string="Custodial Money", readonly=True)

    # === Utilities Electrical === #
    general_sunshine = fields.Text(string="Sunshine")
    utility_phase = fields.Selection(related="projects.status_construction", string="Construction phase", copy=False, index=True, tracking=True, readonly=True, store=True) # redundant default: default='pps',
    e_work_order = fields.Char(string="E. Work Order")
    e_account_number = fields.Char(string="E. Account Number")
    e_type = fields.Selection(selection=[
        ("electrical", "Electrical"),
        ], string="E. Utility Type",
        readonly=True, copy=False, index=True, tracking=True,
        default='electrical')
    e_app_date = fields.Date(string="Electrical Application Date")
    e_conn_type = fields.Selection(selection=[
        ("underground", "Underground"),
        ("overhead", "Overhead"),
        ], string="Electrical Connection Type",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    e_invoice = fields.Boolean(string="Invoice Received")
    elect_meter = fields.Boolean(string="Electric Meter")
    e_utility_provider = fields.Many2one("res.partner", string="Electrical Utility Provider")
    elect_meter_position = fields.Selection(selection=[
        ("left", "Left"),
        ("right", "Right"),
        ], readonly=False, copy=False, index=True, tracking=True,
        default='', string="Electric Meter Position")
    elect_meter_request = fields.Boolean(string="Electric Meter Request")
    e_conn_status = fields.Selection(
        selection=[
            ('disconnected', "Disconnected"),
            ('connected', "Connected")
        ],
        string="Electrical Connection Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    e_comments = fields.Char(string="Comments")
    e_conn_date = fields.Date(string="Electrical Connection Date")
    elect_meter_request_date = fields.Date(string="Electric Meter Request Date")
    e_payment_date = fields.Date(string="Electrical Payment Date")
    elect_utility_engineer = fields.Many2one("res.partner", string="Electric Utility Engineer")
    e_disconn_date = fields.Date(string="Electrical Disconnection Date")
    e_tug = fields.Boolean(string="TUG/PREPOWER")
    e_monthly_bill = fields.Float(string="Monthly Payment Amount (Electrical)")
    e_monthly_payment_date = fields.Integer(string="Monthly Payment Date (Electrical)")
    e_payment_request = fields.Boolean(string="E. Create Payment Request")

    # === Utility Water === #
    w_work_order = fields.Char(string="W. Work Order")
    w_account_number = fields.Char(string="W. Account Number")
    w_app_date = fields.Date(string="Water Application Date")
    w_type = fields.Selection(selection=[
        ("water", "Water"),
        ], string="W. Utility Type",
        readonly=True, copy=False, index=True, tracking=True,
        default='water')
    water_conn_type = fields.Selection(selection=[
        ("well_pump", "Well Pump"),
        ("city_water", "City Water"),
        ], string="Water Connection Type",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    w_invoice = fields.Boolean(string="Is invoice paid?")
    w_utility_provider = fields.Many2one("res.partner", string="Water Utility Provider")
    water_connection_request = fields.Boolean(string="Water Connection Request")
    w_conn_status = fields.Selection(
        selection=[
            ('disconnected', "Disconnected"),
            ('connected', "Connected")
        ],
        string="Water Connection Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    w_comments = fields.Char(string="W. Comments")
    w_conn_date = fields.Date(string="Water Connection Date")
    w_payment_date = fields.Date(string="Water Payment Date")
    w_disconn_date = fields.Date(string="Water Disconnection Date")
    co_date = fields.Date(string="CO Date")
    w_price_sheet = fields.Boolean(string="Price Sheet")
    w_monthly_bill = fields.Float(string="Monthly Payment Amount (Water)")
    w_monthly_payment_date = fields.Integer(string="Monthly Payment Date (Water)")
    w_payment_request = fields.Boolean(string="W. Create Payment Request")


    # === Utility sewage === #
    s_type = fields.Selection(selection=[("sewage", "Sewage"), ("septic regular", "Septic Regular"), ("septic ATU", "Septic ATU"), ("LPS", "LPS")], string="Sewage Type", copy=False, index=True, tracking=True)
    s_installer = fields.Many2one("res.partner", string="Installer")
    s_install_date = fields.Date(string="Installation Date")
    s_agreements = fields.Boolean(string="Maintenance and Operating Agreements")
    s_maop = fields.Date(string="MAOP Date")
    s_inspection_approved = fields.Date(string="Inspection Approved")
    s_inspection_submitted = fields.Date(string="Inspection Submitted")
    s_alarm_wired = fields.Boolean(string="Alarm Wired")
    s_ppi_sent = fields.Boolean(string="PPI Sent")
    s_comments = fields.Char(string="S. Comments")
    s_septic_permit = fields.Char(string="Septic Permit")
    s_sod_installation = fields.Boolean(string="Sod Installation")
    s_sod_installation_date = fields.Date(string="Sod Installation Date")
    s_sod_to_inspection_approved = fields.Integer(string="Sod to Inspection Approved (Days)", help="Days from sod installation to inspection approved", readonly=True, compute="_compute_sod_to_inspection_approved", store=True)

    @api.depends('s_sod_installation_date', 's_inspection_approved')
    def _compute_sod_to_inspection_approved(self):
        for record in self:
            if record.s_sod_installation_date and record.s_inspection_approved:
                delta = record.s_inspection_approved - record.s_sod_installation_date
                record.s_sod_to_inspection_approved = delta.days
            else:
                record.s_sod_to_inspection_approved = 0
         
    has_dumbster = fields.Boolean(string="Has Dumpster", default=False)
    has_toilet = fields.Boolean(string="Has Toilet", default=False)
    
    
    
    is_urgent = fields.Boolean(string="Urgent", default=False)
    portfolio = fields.Many2one("pms.portfolio", string="Portfolio", readonly=True)

    # NO LO ESTAN USANDO CREO CONFIRMAR Y BORRAR
    def scheduled_action_payment_request(self):
        electric_payments = self.search([("e_payment_request", "=", True), ("e_monthly_payment_date", "!=", False)])
        water_payments = self.search([("w_payment_request", "=", True), ("w_monthly_payment_date", "!=", False)])

        for record in electric_payments:
            record.create_payment_request_electric()

        for record in water_payments:
            record.create_payment_request_water()

        # for each utility, create a payment request
    
    # NO LO ESTAN USANDO CREO CONFIRMAR Y BORRAR
    def wrapper_electric_payment_request(self):
        for record in self:
            record.create_payment_request_electric()
    
    # NO LO ESTAN USANDO CREO CONFIRMAR Y BORRAR
    def wrapper_water_payment_request(self):
        for record in self:
            record.create_payment_request_water()

    # NO LO ESTAN USANDO CREO CONFIRMAR Y BORRAR
    def create_payment_request_electric(self, optionalmonth=False):
        self.ensure_one()
        today = date.today()
        if optionalmonth:
            month = optionalmonth
        else:
            month = today.month
        year = today.year
        payment_request = self.env["cc.programmed.payment"].sudo().create({
            "provider": self.e_utility_provider.id,
            "amount": self.e_monthly_bill,
            "payment_date": date(year, month, min(self.e_monthly_payment_date, 28)),
            "request_date": today,
            "properties": [(6, 0, [self.id])],
            "request_type": "utilities",
            })
        
    # NO LO ESTAN USANDO CREO CONFIRMAR Y BORRAR
    def create_payment_request_water(self, optionalmonth=False):
        self.ensure_one()
        today = date.today()
        if optionalmonth:
            month = optionalmonth
        else:
            month = today.month
        year = today.year
        payment_request = self.env["cc.programmed.payment"].sudo().create({
            "provider": self.w_utility_provider.id,
            "amount": self.w_monthly_bill,
            "payment_date": date(year, month, min(self.w_monthly_payment_date, 28)),
            "request_date": today,
            "properties": [(6, 0, [self.id])],
            "request_type": "utilities",
            })




        
    # BORRAR
    def scheduled_actions_on_hold_comments(self):
        for record in self:
            analytic_account_id = record.analytical_account.id

            account_move_lines = record.env['account.move.line'].search([('analytic_distribution', '=', {str(analytic_account_id): 100.0})])
            # latest_on_hold_report = record.env["pms.on.hold.history"].search([("property_name", "=", record.id)], order="id desc", limit=1).comments

            # for line in account_move_lines:
            #     account_move = line.move_id

                # account_move.write({'on_hold_comments': latest_on_hold_report})

    # NO LO ESTAN USANDO CREO CONFIRMAR Y BORRAR
    def on_hold_comments(self):
        analytic_account_id = self.analytical_account.id

        account_move_lines = self.env['account.move.line'].search([('analytic_distribution', '=', {str(analytic_account_id): 100.0})])
        # latest_on_hold_report = self.env["pms.on.hold.history"].search([("property_name", "=", self.id)], order="id desc", limit=1).comments

        # for line in account_move_lines:
        #     account_move = line.move_id

            # account_move.write({'on_hold_comments': latest_on_hold_report})

    
    # TESTED
    @api.depends('partner_id')
    def _compute_own_third(self):
        for record in self:
            company_id = self.env['res.company'].sudo().search([('partner_id', '=', record.partner_id.id)]).ids
            if len(company_id) > 0:
                record.own_third = 'own'
            else:
                record.own_third = 'third'

    # TESTED
    @api.depends('projects.superintendent')
    def _compute_superintendent(self):
        for record in self:
            project_with_superintendent = record.projects.filtered(lambda p: p.superintendent)
            if project_with_superintendent:
                record.superintendent = project_with_superintendent[0].superintendent
            else:
                record.superintendent = False

    # NO SE USA BORRAR
    def get_utilities_payments(self):
        self.ensure_one()
        vendor = self.utility_vendor.id
        analytic_account_id = self.property_address.analytical_account.id
        return {
        'type': 'ir.actions.act_window',
        'name': ('view_account_analytic_line_tree'),
        'res_model': 'account.analytic.line',
        'domain':[("partner_id.id", "=", vendor), ("account_id.id", "=", analytic_account_id)],
        'view_mode': 'tree'}

    # Borrar
    def connect(self):
        self.conn_status = "connected"
        self.disconn_date = False

    # Borrar
    def disconnect(self):
        self.conn_status = "disconnected"
    
    # TESTED
    def set_available(self):
        self.available = True

    # TESTED
    def set_unavailable(self):
        self.available = False

    # TESTED
    def set_available_for_rent(self):
        self.available_for_rent = True

    # TESTED
    def set_unavailable_for_rent(self):
        self.available_for_rent = False

    # TESTED
    def to_coc(self):
        self.status_property = 'coc'

    # Tested
    @api.depends("address", "state_ids", "city", "zipcode", "status_property")
    def _property_full_address(self):
        for record in self:
            string = ""
            if record.status_property == "repair":
                string = "(Repairs) "
            if record.address and record.city and record.state_ids and record.zipcode:
                record.name = f"{string}{record.address} {record.city.name}, {record.state_ids.name} {record.zipcode}"
            else:
                record.name = " "

    # TESTED
    def _property_analytical(self):
        for record in self:
            if record.parcel_id == False:
                raise ValidationError('Please set a parcel id')                
            if record.partner_id.name == False:
                raise ValidationError('Please set a property owner')
            if record.name == False:
                raise ValidationError('Please set all required fields')
            string = ""
            if record.status_property == "repair":
                string = "(Repairs) "
            analytical_acc_name = string + record.name + " " + record.parcel_id + " " + record.partner_id.name

            res = {
                'name': analytical_acc_name,
                'plan_id': record.analytical_plan.id,
                'partner_id': record.partner_id.id,
                'company_id': None
            }

            props_tags = self.env['account.analytic.account'].sudo().create(res)

            record.analytical_account = props_tags.id

        return props_tags.id
    
    # TESTED
    @api.onchange("name", "partner_id")
    def _change_property_analytical(self):
        for record in self:
            if record.analytical_account:
                change_analytical = record.env["account.analytic.account"].search([("id", "=", record.analytical_account.id)])
                change_analytical.sudo().write({"name": record.name + " " + record.parcel_id + " " + record.partner_id.name,
                                                "partner_id": record.partner_id.id})

    # def exclude_from_follow_up(self):
    #     for record in self:
    #         if record.on_hold == True:
    #             follow_up = record.env["account.move.line"].search([("analytic_distribution", "=",  {str(record.analytical_account.id): 100.0})]).move_id.ids
    #             record.env["account.move.line"].search([("move_id", "in", follow_up)]).sudo().write({"blocked" : True})
    #         else: 
    #             pass


    # === Accounting Integrations === #

    # BORRAR
    def update_invoice_types(self):
        for record in self:
            record._update_invoices_on_hold()
            record.projects._update_invoices_custodial_money()

    # BORRAR
    def _update_invoices_on_hold(self):
        analytic_account_id = self.analytical_account.id

        account_move_lines = self.env['account.move.line'].search([('analytic_distribution', '=', {str(analytic_account_id): 100.0})])

        for line in account_move_lines:
            account_move = line.move_id
            company = self.env['res.company'].search([('partner_id', '=', self.partner_id.id)])

            analytic_distributions = account_move.invoice_line_ids.mapped('analytic_distribution')

            valid_analytic_distributions = [
                dist for dist in analytic_distributions 
                if dist and any(key for key, value in dist.items() if value > 0)
            ]

            if len(valid_analytic_distributions) > 1:
                account_move.write({'invoice_type': 'various'})
                continue

            if self.on_hold:
                account_move.write({'invoice_type': 'hold'})
            else:
                if self.custodial_money:
                    account_move.write({'invoice_type': 'escrow'})
                else:
                    if company:
                        account_move.write({'invoice_type': '1stparty'})
                    else:
                        account_move.write({'invoice_type': '3rdparty'})

    
    # BORRAR
    def _prepare_header_bill(self):
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')
        invoice_vals = {
            'ref': '',
            'move_type': move_type,
            'narration': self.description,
            'currency_id': self.company_currency_id.id,
            'partner_id': self.partner_id.id,
            'payment_reference': '',
            'invoice_origin': self.name,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals

    # BORRAR
    def _prepare_line_bills(self):

        res = {
            'display_type': 'product',
            'name': self.name,
            'quantity': 1
        }
        return res

    # BORRAR
    def _prepare_bill(self):
        invoice_list = []
        invoice_list_lines = []
        for record in self:
            vals = record._prepare_header_bill()
            lines = record._prepare_line_bills()
            invoice_list_lines.append(Command.create(lines))
            vals['invoice_line_ids'] += invoice_list_lines
            invoice_list.append(vals)
        
        moves = self.env['account.move'].sudo().create(invoice_list)

        return moves

    # BORRAR
    def _prepare_transaction(self, acc_move, type_tran):

        if type_tran == "purchase":
            res = {
                "name": f"{acc_move.date} {type_tran}, {self.partner_id.name} {acc_move.partner_id.name}",
                "transaction_date": acc_move.date,
                "transaction_type": type_tran,
                "owner":self.partner_id.id,
                "old_owner": acc_move.partner_id.id,
                "transaction_id": acc_move.id
            }
        else:
            res = {
                "name": f"{acc_move.date} {type_tran}, {self.partner_id.name} {acc_move.partner_id.name}",
                "transaction_date": acc_move.date,
                "transaction_type": type_tran,
                "old_owner": self.partner_id.id,
                "transaction_id": acc_move.id
            }
            

        return res
    
    # BORRAR
    def _prepare_sell(self):
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'out_invoice')
        invoice_vals = {
            'ref': '',
            'move_type': move_type,
            'narration': self.description,
            'currency_id': self.company_currency_id.id,
            'payment_reference': '',
            'invoice_origin': self.name,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }

        res = {
            'display_type': 'product',
            'name': self.name,
            'quantity': 1
        }

        invoice_list_lines = []
        invoice_list_lines.append(Command.create(res))

        invoice_vals['invoice_line_ids'] += invoice_list_lines

        moves = self.env['account.move'].sudo().create(invoice_vals)

        return moves
    
    # === Status Buttons === #
    # TESTED
    def to_construction(self):
        if self.mapped('analytical_account'):
            self.status_property = 'construction'
        else:
            self._property_analytical()
            self.status_property = 'construction'
            
    def to_repairs(self):
        if self.mapped('analytical_account'):
            self.status_property = 'repair'
        else:
            self._property_analytical()
            self.status_property = 'repair'
            
    # TESTED
    def to_rent(self):
        if self.mapped('analytical_account'):
            self.status_property = 'rented'
        else:
            self._property_analytical()
            self.status_property = 'rented'
            
            
    # TESTED
    # def put_on_hold(self, auto=False):
    #     if auto:
    #         on_hold_history_list = []
    #         for record in self:
    #             record.on_hold = True
    #             on_hold_data = {
    #                 "property_name": record.id,
    #                 "date": datetime.today(),
    #                 "mail_notification": True,
    #                 "previous_status": record.utility_phase,
    #                 "comments": "",
    #                 "jennys_calls": False,
    #             }
    #             if on_hold_data is not None:
    #                 on_hold_history_list.append(on_hold_data)
    #         self.env["pms.on.hold.history"].sudo().create(on_hold_history_list)
    
    
    def put_on_hold(self, auto=False):
        if auto:
            for record in self:
                record.on_hold = True
        else:
            on_hold_wizard = self.env.ref('pms.view_on_hold_wizard_form')
            return {
                'name': 'On Hold History Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'on.hold.wizard',
                'views': [(on_hold_wizard.id, 'form')],
                'view_id': on_hold_wizard.id,
                'target': 'new',
                'context': {'default_property_id': self.id}
            }
    
    # TESTED
    def put_off_hold(self, auto=False):
        _logger.info("put_off_hold running...")
        
        for record in self:
            
            if record.hold_by_owner and auto:
                _logger.info("put_off_hold skipped because hold_by_owner is True for property %s", record.name)
                message = f'Property {record.name} was put on hold by owner, skipping automatic off hold.'
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'danger',
                    'title': _("Warning"),
                    'message': message,
                    'sticky': False
                })
                continue
            
            record.on_hold = False
            record.date_last_set_on_hold = False
            move_idss = record.env["account.move.line"].search([("analytic_distribution", "=", {str(record.analytical_account.id):100.00})]).move_id.ids
            record.env["account.move.line"].with_context(from_put_off_hold=True).search([("move_id", "in", move_idss)]).sudo().write({"blocked" : False})
            
            if auto:
                _logger.info("put_off_hold running on auto")
                
                history = self.env['pms.on.hold.history'].search([('property_name', '=', self.id), ('hold_end_date', '=', False)], order='date desc')

                for record in history:
                    _logger.info("put_off_hold automatically updating on_hold")
                    record.write({
                        "off_hold_reason": "Closed automatically by odoo",
                        "hold_end_date": datetime.now(),
                    })
            else:
                off_hold_wizard = self.env.ref('pms.view_off_hold_wizard_form')
                return {
                    'name': 'Off Hold Wizard',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'off.hold.wizard',
                    'views': [(off_hold_wizard.id, 'form')],
                    'view_id': off_hold_wizard.id,
                    'target': 'new',
                    'context': {'default_property_id': self.id}
                }

    # TESTED
    def to_draft(self):
        self.mapped('analytical_account').unlink()
        self.status_property = 'draft'

    def purchase_property(self):
    
        return {
        'type': 'ir.actions.act_window',
        'res_model': 'pms.transactions',
        'target': 'current',
        'view_mode': 'form'}

    def sell_property(self):
        return {
        'type': 'ir.actions.act_window',
        'res_model': 'pms.transactions',
        'target': 'current',
        'view_mode': 'form'}
    
    # === Documents functions to override === #
    # BORRAR
    def _get_document_folder(self):
        return self.env["documents.folder"].search([("name", "=", "Properties")])

    # # === Budget Buttons === #
    # @api.depends('house_model')
    # def create_budgets(self):
    #     for records in self:
    #         if records.budget_ids:
    #             raise ValidationError("This property already has a Budget")
             
    #         model_budget_id = records.house_model.budget_model.id
    #         company_budget_id = records.env["res.company"].sudo().search([("partner_id", "=", records.partner_id.id)])
    #         if company_budget_id:
    #             property_budget = records.env["crossovered.budget"].sudo().browse(model_budget_id).sudo().copy(
    #             {"name": records.name,
    #              "company_id": company_budget_id.id}
    #         )
    #         else:
    #             property_budget = records.env["crossovered.budget"].sudo().browse(model_budget_id).sudo().copy(
    #             {"name": records.name})
            
    #         lines_ids = records.env["crossovered.budget.lines"].sudo().search([("crossovered_budget_id", "=", property_budget.id)])
            
    #         for x in lines_ids:
    #             x.sudo().write({
    #                 "analytic_account_id": records.analytical_account.id
    #             })
            
    #         records.budget_ids = property_budget.id




    # === Onchange Methods === #
    # TESTED
    @api.onchange('city')
    def _onchange_city(self):
        if self.city.state:
            self.state_ids = self.city.state
        if self.city.county:
            self.county = self.city.county
    # TESTED
    @api.onchange('state_ids')
    def _onchange_state(self):
        if self.state_ids.country_id:
            self.country_id = self.state_ids.country_id

    def open_arv_wizard(self):
        selected_properties = self.env.context.get('active_ids', [])
        return {
            'name': 'Update ARV',
            'view_mode': 'form',
            'res_model': 'pms.property.arv.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'active_ids': selected_properties,
            }
        }
        

class pms_property_arv_wizard(models.TransientModel):
    _name = "pms.property.arv.wizard"
    _description = "Wizard for Property ARV"

    property_id = fields.Many2one("pms.property", string="Property")
    arv = fields.Float(string="ARV")

    def update_arv(self):
        properties = self.env.context.get('active_ids')
        
        propierties_updated = 0
        
        if not properties:
            raise ValidationError("No property selected.")

        for property in properties:
            property = self.env['pms.property'].browse(property)
            if not property:
                raise ValidationError("Property not found.")
            
            property.arv = self.arv
            propierties_updated += 1
            
        if propierties_updated > 1:
            message = "The ARV for %s properties was updated to: %s." % (propierties_updated, property.arv)
        elif propierties_updated == 1:
            message = "The ARV for %s was updated to: %s." % (property.name, propierties_updated)
        else:
            message = "No properties were updated."

        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': message, 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
        }
    
