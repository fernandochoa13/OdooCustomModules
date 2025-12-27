# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError, UserError

import base64
from collections import defaultdict
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

TYPE_TAX_USE = [
    ('sale', 'Sales'),
    ('purchase', 'Purchases'),
    ('none', 'None'),
]

bill_form = "view_move_form"

class AccountMove(models.Model):
    _inherit = ["account.move"]
    
    # Included in report, removed from original Invoice View
    
    # cambiar approve_bill para que no use analytic_accounts, product_inv
    # borrar las funciones
    # ajustar tablas que usaban estos campos
    
    # Removed
    
    # product_inv = fields.Char(string="Product", compute="_getproduct", store=True) # is being used in  duplicate_products
    # house_model = fields.Char(string="House Model") # is being used in invoice report, remove and replace for pms.property in invoice report
    note_inv = fields.Text(string="Note")
    # invoice_type = fields.Selection(selection=[("3rdparty", "3rd Party"), ("hold", "On Hold"), ("1stparty", "1st Party"), ("escrow", "Escrow Money"), ("various", "Various")], string="Invoice Type",store=True) # compute="_invoice_type_calculate" 
    # last_customer_message = fields.Html(string="Last Customer Message", store=True)
    # on_hold_comments = fields.Text(string="On Hold Comments") 
        
    # # Borrar campo no esta en uso
    # date_receipted = fields.Date(string="Date Receipted")
    
    #########################################################

    analytic_accounts = fields.Char(string="Analytic Account", compute="_getanalytic", store=True) # is being used in approve_bill, duplicate_products and duplicate_reference and pms_materials linked_invoice field
    
    billables = fields.Many2one(comodel_name="account.move", string="Billable Expense")
    invoiced = fields.Many2one(comodel_name="account.move", string="Invoiced Expense")
    recurring_id = fields.Many2one(comodel_name="account.recurring", string="Recurring ID")
    bill_alert = fields.Boolean(string="Bill Alert", default=False)
    bill_price_alert = fields.Boolean(string="Product Price Alert", default=False)
    budget_date = fields.Date(string="Budget Date")
    clear_budget = fields.Boolean(string="Clear Budget", default=False)
    linked_material_order = fields.Many2one("pms.materials", string="Linked Material Order")
    approved = fields.Boolean(string="Approved", default=False)
    checked_duplicate = fields.Boolean(string="Checked Duplicate", default=False)
    contractor = fields.Many2one("res.partner", string="Contractor")
    utility_account_number = fields.Char(string="Utility Account Number")
    utility_pin = fields.Char(string="Utility Pin")
    invoice_link_docs = fields.Char(string="Invoice Link", store=True)
    payment_type_bills = fields.Selection([("check", "Check"), ("online", "Online / CC"), ("material", "Material")], string="Payment Type (Bills)", store=True, default="") # duplicate string
    linked_activities = fields.Many2one("pms.projects.routes", string="Linked Activity")
    activity_completed = fields.Boolean(related="linked_activities.completed", string="Activity Completed", store=True, readonly=False, inverse="_inverse_activity_completed")
    def _inverse_activity_completed(self):
        for record in self:
            if record.activity_completed == True:
                record.linked_activities._complete_jobs()
            if record.activity_completed == False:
                record.linked_activities.uncomplete_jobs()
        return 
    qb_payment = fields.Boolean()
    salesperson_followup = fields.Char(string="Salesperson Followup")
    service_fee = fields.Float(string="Service Fee", default=0.032) 
    employee_id = fields.Many2one("hr.employee", string="Employee")
    comments = fields.Char(string="Comments")

    priority = fields.Selection([('0', 'None'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority', default='0', store=True)
    contractor_date = fields.Date(string="Contractor Date")
    
    linked_contractor_job = fields.Many2one("pms.contractor.job", string="Linked Contractor Job")
    
    date = fields.Date(
        string='Date',
        index=True,
        compute='_compute_date', store=True, required=True, readonly=False, precompute=True,
        copy=False,
        tracking=True,
    )

    cash_date = fields.Date(string="Cash Basis Date", store=True, compute="_compute_cash_match_date")
    partial = fields.Boolean(string="paid in portions", default=False)
 

    @api.depends('payment_state', 'line_ids.matching_number', 'date')
    def _compute_cash_match_date(self):
        if not self:
            return

        _logger.info("lines moves_bank_cash filtered running...")
        # We use filtered_domain to filter in python and dont hit the db yet
        lines_to_process = self.line_ids.filtered_domain(["&", ("parent_state", "=", "posted"), "&", ("journal_id.type", "not in", ("bank", "cash")), "|", ("account_id.account_type", "=", "asset_receivable"), ("account_id.account_type", "=", "liability_payable")])
        _logger.info(f"lines moves_bank_cash {lines_to_process}...")
        final_dates = {}
        
        # This is not costly because of odoo orm prefetching
        for move in self:
            _logger.info(f"move: {move}...")
            if move.state == 'posted':
                final_dates[move.id] = move.date

        #receivable_lines = lines_to_process.filtered_domain([("")])
        #payable_lines = lines_to_process.filtered(
        #    lambda l: l.account_id.account_type == 'liability_payable' and l.balance < 0
        #)
        
        for line in lines_to_process:
            _logger.info(f"line: {line}...")
            account_type = line.account_type

            balance = line.balance
            _logger.info("lines _compute_match_date running...")
            if line.matching_number != False:
                date = False
                # Check how to prefetch the .mapped
                if account_type == 'asset_receivable' and balance > 0.00:
                    date = line.mapped("matched_credit_ids.credit_move_id.date")
                elif account_type == 'liability_payable' and balance < 0.00:
                    date = line.mapped("matched_debit_ids.debit_move_id.date")
                if date:
                    _logger.info(f"_compute_match_date running {date}...")
                    if len(date) > 1 or line.matching_number == "P":
                        line.move_id.with_context(bypass_compute=True).write({"partial": True})
                    max_date = max(date)
                    _logger.info(f"_compute_match_date running max date {max_date}...")
                    _logger.info("date: " + str(max_date))
                    final_dates[line.move_id.id] = max_date
            else:
                del final_dates[line.move_id.id]
            
        _logger.info(final_dates)
        if not final_dates:
            return

        params = []
        placeholders = []
        for line_id, date_value in final_dates.items():
            placeholders.append('(%s, %s)')
            params.extend([line_id, date_value or None])

        placeholders_str = ', '.join(placeholders)
        

        query = f"""
            UPDATE account_move
            SET cash_date = data.cash_date
            FROM (VALUES {placeholders_str}) AS data(id, cash_date)
            WHERE account_move.id = data.id
        """

        self.env.cr.execute(query, params)


        self.invalidate_recordset(['cash_date'])
        self.modified(['cash_date'])
        _logger.info("Query executed")

        
                        

    
    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        """
        Overrides the standard _compute_name to force a re-sequence
        when the date field is changed on a move.
        """
        # A flag to check if only the date was modified.
        # This is a good practice to avoid unintended side effects.
        # It's better to check if the date is in the modified fields.
        if self.env.context.get('force_resequence_on_date_change'):
            for move in self.filtered(lambda m: m.date and not m.name):
                move._set_next_sequence()
        else:
            # Fallback to the original function for all other scenarios.
            # This is important to not break core Odoo functionality.
            super(AccountMove, self)._compute_name()


    def _set_next_sequence_on_date_change(self):
        """
        This is a new helper function that you can call from a button or
        an onchange method to force the sequence update.
        """
        for move in self:
            # We want to re-run the _compute_name to update the sequence.
            # We must use a context key to signal the override.
            move.with_context(force_resequence_on_date_change=True)._compute_name()


    @api.onchange('date')
    def _onchange_date_resequence(self):
        """
        This method will be triggered whenever the 'date' field is changed.
        It calls the helper function to recompute the sequence.
        """
        self._set_next_sequence_on_date_change()


    @api.onchange('date')
    def _onchange_date_clear_name(self):
        """
        Clears the name field when the date is changed, forcing a recomputation
        when the move is saved.
        """
        self.name = False
        
    def create(self, vals_list):
        invoices = super().create(vals_list)
        for invoice in invoices:
            if invoice.linked_contractor_job:
                invoice.linked_contractor_job.write({'linked_invoice': invoice.id})
        # if invoices:
        #     # Insert only the new records
        #     self.env["account.report"]._insert_cash_basis_entries_for_moves(invoices.ids, False)
        return invoices
    
    def write(self, vals):
        # Store the current linked_contractor_job before the write operation
        # This gives us the 'old' value for each record in 'self'
        old_linked_jobs = {record.id: record.linked_contractor_job for record in self}

        # Perform the actual write operation
        res = super().write(vals)
        _logger.info(vals)
        # if res:
        #     state = False
        #     if "state" in vals:
        #         state = f"'{vals['state']}'"
            
        #     self.env["account.report"]._update_cash_basis_entries_for_moves(self.ids, state)

        # Iterate over the records after the write to get the 'new' value
        for record in self:
            old_job = old_linked_jobs.get(record.id) # The job linked before the write
            new_job = record.linked_contractor_job    # The job linked after the write

            # Case 1: A new linked_contractor_job is set or updated
            if new_job and new_job != old_job:
                new_job.write({'linked_invoice': record.id})

            # Case 2: The linked_contractor_job was unset or changed from an old one
            if old_job and new_job != old_job:
                # IMPORTANT: Only clear if the old job's linked_invoice *was* this record.
                # This avoids clearing an invoice link if the old job was linked to a different invoice.
                if old_job.linked_invoice and old_job.linked_invoice.id == record.id:
                    old_job.write({'linked_invoice': False})
                    
            # if 'invoice_line_ids' in vals:
            #     _logger.info("The bill is either being posted or a line item was updated. Checking for related programmed payment.")
            #     # Search for the related 'cc.programmed.payment' record using the bill_id.
            #     programmed_payment = self.env['cc.programmed.payment'].sudo().search([
            #         ('bill_id', '=', record.id)
            #     ], limit=1)

            #     if programmed_payment:
            #         _logger.info(f"Programmed payment found. Updating amount to: {record.amount_total_signed}")
            #         # Update the 'amount' field of the programmed payment.
            #         programmed_payment.sudo().write({
            #             'amount': abs(record.amount_total_signed),
            #         })
            #     else:
            #         _logger.info("No programmed payment found for this bill.")
        return res
    
    
    property_id = fields.Many2one('pms.property', string='Property', compute='_compute_property_id', store=True, inverse="_inverse_property")
    def _inverse_property(self):
        return
    status_property = fields.Selection(related='property_id.status_property',
        selection=[
            ('draft', "Draft"),
            ('construction', "Construction"),
            ('coc', "COC"),
            ('rented', "Rented"),
            ('sold', "Sold"),
            ('repair', "Repair"),
        ], string='Property Status', store=True, readonly=True)
    
    custodial_money = fields.Boolean(related='property_id.custodial_money', string='Custodial Money', store=True, readonly=True)
    
    property_house_model = fields.Many2one(related='property_id.house_model', string='House Model', store=True, readonly=True)
    
    lock_on_coc = fields.Boolean(string="Lock on COC", default=False, store=True, readonly=True, compute="_compute_lock_on_coc")
    
    coc_approved = fields.Boolean(string="COC Approved", default=False, store=True, readonly=True)
    is_invoice_admin = fields.Boolean(
        string="Is Invoice Admin",
        compute='_compute_is_invoice_admin',
        help="Technical field to check if the current user is an invoice administrator.",
        readonly=True
    )
    
    def button_draft(self):
        """
        Inherits the original button_draft function and adds logic
        to reset the 'coc_approved' flag.
        """
        # Call the original function first to execute its logic
        res = super(AccountMove, self).button_draft()
        
        # Then, add our custom logic
        for rec in self:
            if rec.lock_on_coc:
                rec.coc_approved = False
        
        return res
    
    @api.depends('company_id.partner_id.user_ids')
    def _compute_is_invoice_admin(self):
        """
        Check if the current user is in a specific invoice admin security group.
        You should link this to your actual security group in your module.
        For now, this is a placeholder.
        """
        for move in self:
            group = 'pms.group_invoice_admin'
            move.is_invoice_admin = self.env.user.has_group(group)

    def action_approve_coc(self):
        """
        Sets the coc_approved field to True, which will make the banner disappear.
        """
        self.ensure_one()
        self.coc_approved = True
        
    @api.depends('property_id.status_property')
    def _compute_lock_on_coc(self):
        _logger.info("_compute_lock_on_coc running...")
        for record in self:
            if record.property_id and record.property_id.status_property == 'coc':
                record.lock_on_coc = True
            else:
                record.lock_on_coc = False
    
    invoice_filter_type = fields.Selection(string="Invoice Category", store=True, readonly=False,
        selection=[('cfl_construction', 'CFL Construction'), 
                   ('contractor', 'Contractor'), 
                   ('interior_labor', 'Interior Labor'), 
                   ('roof_labor', 'Roof Labor'), 
                   ('slab_block', 'Slab & Blocks'), 
                   ('card', 'Card'), 
                   ('crew', 'Crew'),
                   ('materials', 'Materials'), 
                   ('anticipated', 'Anticipated'), 
                   ('checks', 'Checks'), 
                   ('engineering_gc', 'Engineering & GC'), 
                ]
        )

    @api.depends('analytic_accounts')
    def _compute_property_id(self):
        def split_properties(analytic_accounts):
            properties = []
            parts = analytic_accounts.split(',')
            i = 0
            while i < len(parts) - 1:
                properties.append(f"{parts[i]},{parts[i+1]}")
                i += 2
            return properties
        for record in self:
            if record.analytic_accounts:
                properties = split_properties(record.analytic_accounts)
                for property_name in properties:
                    record.property_id = self.env['pms.property'].search([('analytical_account.name', '=', property_name)], limit=1)
                    return

    
    def open_contractor_job(self):
        for record in self:
            if record.linked_contractor_job:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Contractor Job',
                    'res_model': 'pms.contractor.job',
                    'view_mode': 'form',
                    'res_id': record.linked_contractor_job.id,
                    'target': 'current',
                }
            else:
                raise ValidationError(_("No linked contractor job found."))
    
    invoice_date_paid = fields.Date(string="Invoice Date Paid")
    completed_date = fields.Date(string="Completed Date")
    date_paid = fields.Date(string="Invoice Date Paid", store=True, compute="_compute_match_date")
    @api.depends('payment_state')
    def _compute_match_date(self):
        _logger.info("_compute_match_date running...")
        for move in self:
            if move.payment_state in ['paid', 'partial', 'in_payment']:
                date = False
                if move.move_type == 'out_invoice':
                    # date = move.mapped("line_ids.matched_credit_ids.max_date")
                    date = move.mapped("line_ids.matched_credit_ids.credit_move_id.date")
                elif move.move_type == 'in_invoice':
                    # date = move.mapped("line_ids.matched_debit_ids.max_date")
                    date = move.mapped("line_ids.matched_debit_ids.debit_move_id.date")
                if date:
                    date = max(date)
                    _logger.info("date: " + str(date))
                    move.date_paid = date
                else:
                    _logger.info("no date found.")
                    move.date_paid = False
    # Override readonly from original account_move
    
    invoice_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment Terms',
        compute='_compute_invoice_payment_term_id', store=True, readonly=False, precompute=True,
        check_company=True,
    )
    
    invoice_date = fields.Date(
        readonly=False
    )
    
    # Redefinition removed - using first declaration above

    
    invoice_line_ids = fields.One2many(  # /!\ invoice_line_ids is just a subset of line_ids.
        'account.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        readonly=False,
        domain=[('display_type', 'in', ('product', 'line_section', 'line_note'))],
    )
    
    line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Journal Items',
        copy=True,
        readonly=False,
    )
    
    """
    def _compute_house_model(self):
        for line in self.invoice_line_ids:
            if line.analytic_distribution:
                analytic_account_ids = [int(analytic_id) for analytic_id in line.analytic_distribution.keys()]
                property = self.env['pms.property'].search([('analytical_account', 'in', analytic_account_ids)], limit=1)
                if property:
                    self.house_model = property.house_model.name
                    break
                else:
                    _logger.warning(f"Property {property.name} has no house_model.") 
                    self.house_model = "No House Model" 
                    break10/01/2025 
        return
    """
    @api.onchange("contractor")
    def update_invoice_payment_term(self):
        for record in self:
            if record.contractor and record.contractor.contractor_payment_terms and record.move_type == "out_invoice":
                record.invoice_payment_term_id = record.contractor.contractor_payment_terms.id
            elif record.invoice_payment_term_id and record.move_type == "out_invoice":
                # If contractor is not set, keep the existing payment term
                _logger.info("Contractor not set, keeping existing payment term: %s", record.invoice_payment_term_id.name)
                continue
            else:
                record.invoice_payment_term_id = False
    
    
    def _inverse_tax_totals(self):
        if self.env.context.get('skip_invoice_sync'):
            return
        with self._sync_dynamic_line(
            existing_key_fname='term_key',
            needed_vals_fname='needed_terms',
            needed_dirty_fname='needed_terms_dirty',
            line_type='payment_term',
            container={'records': self},
        ):
            for move in self:
                if not move.is_invoice(include_receipts=True):
                    continue
                invoice_totals = move.tax_totals

                if not isinstance(invoice_totals, dict):
                    return

                for amount_by_group_list in invoice_totals['groups_by_subtotal'].values():
                    for amount_by_group in amount_by_group_list:
                        tax_lines = move.line_ids.filtered(lambda line: line.tax_group_id.id == amount_by_group['tax_group_id'])

                        if tax_lines:
                            first_tax_line = tax_lines[0]
                            tax_group_old_amount = sum(tax_lines.mapped('amount_currency'))
                            sign = -1 if move.is_inbound() else 1
                            delta_amount = tax_group_old_amount * sign - amount_by_group['tax_group_amount']

                            if not move.currency_id.is_zero(delta_amount):
                                first_tax_line.amount_currency -= delta_amount * sign
            self._compute_amount()
    
    # @api.onchange('linked_activities')
    # def _onchange_linked_activities(self):
    #     if self.linked_activities:
    #         self.activity_completed = self.linked_activities.completed
    #         # self.date_receipted = self.linked_activities.end_date
    
    
    def open_linked_activities(self):
        self.ensure_one()
        return {
        'type': 'ir.actions.act_window',
        'name': ('pms_projects_routes_tree'),
        'res_model': 'pms.projects.routes',
        'domain':[("id", "=", self.linked_activities.id)],
        'view_mode': 'tree'}

    @api.depends("line_ids.analytic_distribution")
    def _getanalytic(self):
        _logger.info("analytic_accounts running...")
        for record in self:
            analytic_ids = record.env["account.move.line"].sudo().search([("move_id", "=", record.id)])
            if analytic_ids:
                address_final = set()
                for analytic_id in analytic_ids:
                    analytic_i = analytic_id.analytic_distribution
                    if analytic_i:
                        for key in analytic_i.keys():
                            address = record.env["account.analytic.account"].sudo().search([("id", "=", key)]).name
                            address_final.add(address) 
                
                string_addresses = [str(addr) for addr in address_final]
                unique_addresses = ",".join(sorted(string_addresses))
                record.analytic_accounts = unique_addresses
            else:
                record.analytic_accounts = False

    # @api.depends("line_ids.product_id")
    # def _getproduct(self):
    #     _logger.info("_getproduct running...")
    #     for record in self:
    #         product_ids = record.env["account.move.line"].sudo().search([
    #                 ("move_id", "=", record.id)
    #             ]).product_id.mapped("name")
    #         if product_ids:
    #             product_name = ','.join(product_ids)
    #             record.product_inv = product_name
    #         else:
    #             record.product_inv = False



    # @api.depends("line_ids.display_type")
    # def _getnote_inv(self):
    #     _logger.info("_getnote_inv running...")
    #     for record in self:
    #         note_ids = record.env["account.move.line"].sudo().search(["&", ("display_type", "=", "line_note"), ("move_id", "=", record.id)])
    #         section = record.env["account.move.line"].sudo().search(["&", ("display_type", "=", "line_section"), ("move_id", "=", record.id)])
    #         if section: 
    #             section_i = []
    #             for sec in section:
    #                 section_i.append(sec.name)
    #             section_i = ",".join(str(element) for element in section_i)
    #             record.note_inv = section_i
    #         elif note_ids:
    #             notes_i = []
    #             for note in note_ids:
    #                 notes_i.append(note.name)

    #             notes_i = ",".join(str(element) for element in notes_i)
    #             record.note_inv = notes_i
    #         else:
    #             record.note_inv = ""
    
    # Funcion anterior
    # @api.depends('last_customer_message')
    # def _get_last_customer_message(self):
    #     yesterday = (datetime.now() - timedelta(days=1)).date()
    #     start_datetime = datetime.combine(yesterday, datetime.min.time())
    #     end_datetime = datetime.combine(yesterday, datetime.max.time())

    #     messages = self.env['mail.message'].search([
    #         ('model', '=', 'account.move'),
    #         ('date', '>=', start_datetime),
    #         ('date', '<=', end_datetime)
    #     ], order='write_date desc')
    #     for record in self:
    #         last_message_body = ""
    #         for msg in messages:
    #             if msg.res_id == record.id:
    #                 last_message_body = msg.body
    #                 break
    #         record.last_customer_message = last_message_body
            
    # Funcion optimizada
    @api.depends('last_customer_message')
    def _get_last_customer_message(self):
        
        yesterday = (datetime.now() - timedelta(days=1)).date()
        start_datetime = datetime.combine(yesterday, datetime.min.time())
        end_datetime = datetime.combine(yesterday, datetime.max.time())
        
        for record in self:
            
            last_message_body = ""
            message = self.env['mail.message'].search([
                ('model', '=', 'account.move'),
                ('res_id', '=', record.id),
                ('date', '>=', start_datetime),
                ('date', '<=', end_datetime),
            ], order='write_date desc', limit=1)
            
            if message:
                last_message_body = message.body
                
            record.last_customer_message = last_message_body
    


    # @api.depends('invoice_line_ids')
    # def _compute_house_model(self):
    #     for move in self:  
    #         house_model_name = "No House Model" 
    #         for line in move.invoice_line_ids:
    #             if line.analytic_distribution:
    #                 analytic_account_ids = [int(analytic_id) for analytic_id in line.analytic_distribution.keys()]
    #                 property = self.env['pms.property'].search([('analytical_account', 'in', analytic_account_ids)], limit=1)
    #                 if property and property.house_model: 
    #                     house_model_name = property.house_model.name
    #                     break 
    #                 elif property: # Property Found, but no house_model
    #                     _logger.warning(f"Property {property.name} has no house_model.")
    #                 else: # Property not found
    #                     _logger.warning(f"No property found with analytic accounts {analytic_account_ids}")

    #         move.house_model = house_model_name



    def off_hold_preprocessor(self):
        _logger.info("off_hold_preprocessor running...")
        self.ensure_one()
        analytics_checked = []
        for invoice_line in self.line_ids:
            if invoice_line.analytic_distribution:
                _logger.info("invoice_line.analytic_distribution found:" + str(invoice_line.analytic_distribution))
                
                for analytic_id in invoice_line.analytic_distribution.keys():
                    if analytic_id in analytics_checked:
                        _logger.info("analytic_id in analytics_checked")
                        continue
                    else:
                        _logger.info("searching for property")
                        _logger.info("analytic_id:" + analytic_id)
                        property = self.env['pms.property'].search([
                        ('analytical_account', '=', int(analytic_id))
                        ])
                        _logger.info(property)
                        
                        if property.on_hold:
                            _logger.info("property on hold found")
                            self.check_off_hold(property)
                            analytics_checked.append(analytic_id)

    def check_off_hold(self, property_obj):
        _logger.info("check_off_hold running...")
        
        self.ensure_one()
        # Check for invoices that are still unpaid (not_paid or partial) and are 3+ days overdue
        # When invoices go to "in_payment" status, they are being processed, so they should NOT keep the property on hold
        # Only invoices that are still "not_paid" or "partial" should keep the property on hold
        pending_invoices = self.env['account.analytic.line'].search([
            ('account_id', '=', property_obj.analytical_account.id),
            ('category', '=', 'invoice'),
            ('move_line_id.move_id.payment_state', 'in', ('not_paid', 'partial')),
            ('move_line_id.move_id.invoice_date_due', '<', fields.Date.today() - timedelta(days=3)),
        ])
        
        # Filter out invoices with Advance Payment terms (anticipated_payment = TRUE)
        # Also exclude utility_payment and material_payment terms for consistency
        filtered_invoices = self.env['account.analytic.line']
        for inv_line in pending_invoices:
            move = inv_line.move_line_id.move_id
            if move.invoice_payment_term_id:
                payment_term = move.invoice_payment_term_id
                # Exclude Advance Payment, Utility Payment, and Material Payment terms
                if not payment_term.anticipated_payment and not payment_term.utility_payment and not payment_term.material_payment:
                    filtered_invoices |= inv_line
            else:
                # Include invoices without payment terms
                filtered_invoices |= inv_line
        
        pending_invoices = filtered_invoices

        if len(pending_invoices.ids) > 0:
            message = f'Property {property_obj.name} still has outstanding pending invoices.'
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'danger',
                'title': _("Warning"),
                'message': message,
                'sticky': True
            })
            return
        else:
            # Correo de que se puso off hold
            # quitar del hold
            property_obj.put_off_hold(auto=True)
            message = f'Property {property_obj.name} automatically put off hold.'
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': message, 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
            }
            # q mande una notificacion

            # Q envie un correo al partner

    def check_on_hold(self):

        query = """
            SELECT
                pms_property.id AS property_id,
                ARRAY_AGG(account_move.id) AS invoice_ids
            FROM pms_property
            INNER JOIN
                (
                    SELECT
                        account_analytic_line.account_id AS account_id,
                        account_move.id AS move_id
                    FROM account_analytic_line
                    INNER JOIN account_move_line ON account_analytic_line.move_line_id = account_move_line.id
                    INNER JOIN account_move ON account_move_line.move_id = account_move.id
                    LEFT JOIN account_payment_term apt ON account_move.invoice_payment_term_id = apt.id
                    WHERE account_analytic_line.category = 'invoice'
                    AND (
                        (account_move.payment_state IN ('not_paid', 'partial') AND account_move.invoice_date_due + INTERVAL '4 days' < CURRENT_DATE)
                    )
                    AND account_move.linked_material_order IS NULL
                    AND account_move.move_type NOT IN ('out_refund', 'in_refund') 
                    AND (apt.utility_payment = FALSE OR apt.utility_payment IS NULL)
                    AND (apt.material_payment = FALSE OR apt.material_payment IS NULL)
                    AND (apt.anticipated_payment = FALSE OR apt.anticipated_payment IS NULL)
                ) AS sq1 ON pms_property.analytical_account = sq1.account_id
            INNER JOIN pms_projects ON pms_property.id = pms_projects.address
            INNER JOIN account_move ON sq1.move_id = account_move.id
            WHERE pms_property.on_hold = FALSE
            AND pms_property.own_third = 'third'
            AND account_move.company_id IN (42, 46, 47, 48, 49) -- CFL Rehabbers(42), 3rd Party (46), ADG Homes (47), Tetcho Roofing (49) CFL Construction (48) 
            AND account_move.partner_id = pms_property.partner_id
            -- AND pms_property.exclude_on_hold = FALSE
            AND pms_projects.custodial_money = FALSE
            GROUP BY pms_property.id
        """


        self.env.cr.execute(query)
        results = self.env.cr.fetchall()

        on_hold_history_list = []
        property_ids_list = []
        
        for property_id, invoice_ids in results:
            _logger.info("Property ID: %s, Invoice IDs: %s", property_id, invoice_ids)
            
            property_ids_list.append(property_id)
            
            invoices = self.env['account.move'].browse(invoice_ids)
            unique_product_ids = invoices.invoice_line_ids.mapped('product_id').ids
            
            on_hold_data = {
                "property_name": property_id,
                "date": datetime.today(),
                "mail_notification": True,
                "previous_status": self.env['pms.property'].browse(property_id).utility_phase,
                "comments": "",
                "jennys_calls": False,
                "invoice_ids": [(4, invoice_id, 0) for invoice_id in invoice_ids],
                "product_ids": [(6, 0, unique_product_ids)],
            }
            on_hold_history_list.append(on_hold_data)
            _logger.info("On Hold Data: %s", on_hold_data)
            _logger.info("On Hold History List Data: %s", on_hold_history_list)
        properties_to_put_hold = self.env['pms.property'].browse(property_ids_list)
        properties_to_put_hold.put_on_hold(auto=True)
        history = self.env["pms.on.hold.history"].sudo().create(on_hold_history_list)
        _logger.info("history created: %s", history)
        _logger.info("history invoice created: %s", history.invoice_ids)
        _logger.info("Properties put on hold through check_on_hold(): %s", str(len(properties_to_put_hold)))
    
    # def calculate_service_fee(self): # add logic to allow bills to have service fee?
    #     for record in self:
    #         if record.move_type == 'out_invoice':
    #             if record.state == 'posted':
    #                 raise ValidationError("Service Fee can only be calculated for draft invoices.")
    #             else:
    #                 for invoice_line in record.line_ids:
    #                     invoice_line.price_unit = invoice_line.price_unit + (record.service_fee * invoice_line.price_unit)
    #                 record.message_post(body="Service Fee Calculated")
    #         else:
    #             raise ValidationError("Service Fee can only be calculated for invoices.")

    @api.depends(
#        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
 #       'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.full_reconcile_id',
        'state')
    def _compute_amount(self):
        for move in self:
            total_untaxed, total_untaxed_currency = 0.0, 0.0
            total_tax, total_tax_currency = 0.0, 0.0
            total_residual, total_residual_currency = 0.0, 0.0
            total, total_currency = 0.0, 0.0

            for line in move.line_ids:
                if move.is_invoice(True):
                    # === Invoices ===
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type in ('product', 'rounding'):
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            sign = move.direction_sign
            move.amount_untaxed = sign * total_untaxed_currency
            move.amount_tax = sign * total_tax_currency
            move.amount_total = sign * total_currency
            move.amount_residual = -sign * total_residual_currency
            move.amount_untaxed_signed = -total_untaxed
            move.amount_tax_signed = -total_tax
            move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            move.amount_residual_signed = total_residual
            move.amount_total_in_currency_signed = abs(move.amount_total) if move.move_type == 'entry' else -(sign * move.amount_total)
            move._compute_payment_state()

    
    def calculate_service_fee(self): # add logic to allow bills to have service fee?
        for record in self:
            for invoice_line in record.line_ids:
                invoice_line.price_unit = invoice_line.price_unit + (record.service_fee * invoice_line.price_unit)
            record.message_post(body="Service Fee Calculated")


    def calculate_tax(self):
        for record in self:
            if record.move_type == 'out_invoice':
                if record.state == 'posted':
                    raise ValidationError("Tax can only be calculated for draft invoices.")
                else:
                    for invoice_line in record.line_ids:
                        if invoice_line.analytic_distribution:
                            analytic_account_ids = [int(analytic_id) for analytic_id in invoice_line.analytic_distribution.keys()]
                            if not analytic_account_ids:
                                raise ValidationError("Analytic Account is required to calculate tax.")

                            properties = self.env['pms.property'].search([
                            ('analytical_account', 'in', analytic_account_ids)
                        ])
                            tax_apply = self.env['account.tax'].search([('county', '=', properties.county.id)], limit=1)
                            state_tax = self.env['account.tax'].search([('name', '=', 'State Tax')], limit=1)
                            if tax_apply and state_tax:
                                invoice_line.tax_ids = [(6, 0, [tax_apply.id, state_tax.id])]  

            else:
                raise ValidationError("Tax can only be calculated for invoices.")

    def open_message_crm_wizard(self):
        for record in self:
            if not record.partner_id.email:
                raise ValidationError(_("Email field cannot be empty."))
            if not record.partner_id.phone and not record.partner_id.mobile:
                raise ValidationError(_("Either phone or mobile field must be filled."))

        wizard_view = self.env.ref('pms.view_message_crm_wizard_form')
        first_name = self.partner_id.display_name.split(' ')[0]
        last_name = self.partner_id.display_name.split(' ')[1]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'message.crm.wizard',
            'view_id': wizard_view.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_invoice_id': self.id,
                'default_contact_id': self.partner_id.contact_id if self.partner_id.contact_id else None,
                'default_first_name': first_name,
                'default_last_name': last_name,
                'default_email': self.partner_id.email,
                'default_phone_number': self.partner_id.phone or self.partner_id.mobile,
            },
        }

    def action_invoice_sent(self):
        self.ensure_one()

        res = super(AccountMove, self).action_invoice_sent()

        if isinstance(res, dict) and 'context' in res:
            ctx = res['context']

            all_attachment_ids = []

            attachments_on_invoice = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
            ])
            if attachments_on_invoice:
                all_attachment_ids.extend(attachments_on_invoice.ids)
                _logger.info("Found %s attachments directly on invoice '%s' (ID: %s). IDs: %s",
                             len(attachments_on_invoice), self.name, self.id, attachments_on_invoice.ids)
            else:
                _logger.info("No direct attachments found on invoice '%s' (ID: %s).",
                             self.name, self.id)

            if self.linked_contractor_job:
                job_attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'pms.contractor.job'),
                    ('res_id', '=', self.linked_contractor_job.id),
                ])
                if job_attachments:
                    all_attachment_ids.extend(job_attachments.ids)
                    _logger.info("Found %s attachments on linked contractor job '%s' (ID: %s). IDs: %s",
                                 len(job_attachments), self.linked_contractor_job.name, self.linked_contractor_job.id, job_attachments.ids)
                else:
                    _logger.info("No attachments found on linked contractor job '%s' (ID: %s).",
                                 self.linked_contractor_job.name, self.linked_contractor_job.id)
            else:
                _logger.info("No contractor job linked to invoice '%s' (ID: %s).",
                             self.name, self.id)


            default_attachment_ids = ctx.get('default_attachment_ids', [])
            _logger.info("Default attachments from super() (includes auto-generated PDF): %s", default_attachment_ids)

            combined_attachments = list(set(default_attachment_ids + all_attachment_ids))

            _logger.info("Final combined attachments to set in context: %s", combined_attachments)

            ctx['default_attachment_ids'] = [(6, 0, combined_attachments)]
            res['context'] = ctx

        return res
            
    def request_payment(self):
        _logger.info(f"request_payment called for move: {self.name}")
        try:
            # Check if a payment request already exists for this bill
            _logger.info("Checking for existing payment request...")
            existing_payment_request = self.env['cc.programmed.payment'].sudo().search([
                ('bill_id', '=', self.id)
            ], limit=1)
            _logger.info(f"Existing payment request: {existing_payment_request}")

            if existing_payment_request:
                # Payment request already exists, return action to open it
                _logger.info("Payment request already exists.")

                message = _(f"Payment request '{existing_payment_request.name}' found.")

                # Send notification
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'info',
                    'title': _("Payment Request Info"),
                    'message': message,
                    'action': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'cc.programmed.payment',
                        'view_mode': 'form',
                        'res_id': existing_payment_request.id,
                        'target': 'current',
                    }
                })

                # Add styled message and action link to notes
                action_link = _(f"<a href='#' data-oe-model='cc.programmed.payment' data-oe-id='{existing_payment_request.id}'>View Payment Request</a>")
                notes = f'''
                    <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                        <b>Payment Request:</b><br>
                        <i>{message} {action_link}</i>
                    </div>
                '''

                self.message_post(body=notes)

                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'cc.programmed.payment',
                    'view_mode': 'form',
                    'res_id': existing_payment_request.id,
                    'target': 'current',
                }
                
            # If no existing payment request, proceed to create a new one
            _logger.info("Creating new payment request...")
            property_ids = []

            for line in self.invoice_line_ids:
                if line.analytic_distribution:
                    analytic_account_ids = [int(analytic_id) for analytic_id in line.analytic_distribution.keys()]

                    properties = self.env['pms.property'].search([
                        ('analytical_account', 'in', analytic_account_ids)
                    ])

                    property_ids.extend(properties.ids)

            property_ids = list(set(property_ids))
            _logger.info(f"Property IDs: {property_ids}")

            record = self.env['cc.programmed.payment'].sudo().create({
                'requested_by': self.employee_id.id,
                'provider': self.partner_id.id,
                'amount': self.amount_total,
                'company': self.company_id.id,
                'request_date': fields.Date.today(),
                'payment_date': self.invoice_date_due,
                'concept': self.payment_reference,
                'properties': [(6, 0, property_ids)],
                'bill_id': self.id,
                'has_bill': True,
            })
            _logger.info(f"Payment request created: {record.id}")

            return {
                'name': 'Credit Card Programmed Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'cc.programmed.payment',
                'view_mode': 'form',
                'res_id': record.id,
                'target': 'current',
            }

        except Exception as e:
            _logger.error(f"Error in request_payment: {e}")
            raise # re-raise the exception so it is visible in the Odoo UI.


    def open_intercompany_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Intercompany Payment',
            'view_mode': 'form',
            'res_model': 'intercompany.wizard',
            'target': 'new',
            'context': {'default_company_id': self.company_id.id, 
                        'default_amount_total': self.amount_total_signed, 
                        'default_provider': self.partner_id.id,
                        'default_id': self.id,
                        'references': self.payment_reference}
        }

    def create_material_order(self):
        orders_form = self.env.ref('pms.create_materials_order_wizard_form')
        return {
                'name': 'Material Orders Wizard',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'material.orders.wizard',
                'views': [(orders_form.id, 'form')],
                'view_id': orders_form.id,
                'target': 'new',
                'context': {'default_invoice_line_ids': self.invoice_line_ids.ids,
                            'default_partner_id': self.partner_id.id,
                            # 'default_date_receipted': self.date_receipted,
                            'default_invoice_date': self.invoice_date,
                            'default_bill_id': self.id}  
            }

    # Funcion base de cancelar en account move
    
    def cancel_journal(self):
        
        journals = self.env.context.get('active_ids')
        cancelled = []
        
        if not journals:
            return self.env['update.owner.call.day'].simple_notification("error", "Error", "Unable to find any records to update.", False)
        
        for journal in journals:
            selected_journal = self.env['account.move'].search([('id', '=', journal)])
            
            if not selected_journal: continue
            
            selected_journal.update({'auto_post': 'no', 'state': 'cancel'})
            cancelled.append(selected_journal)
        
        if len(cancelled) > 1: message = "%s journal entries cancelled." % len(cancelled)
        else: message = "Journal entry cancelled."
        
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': message, 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
        }
    
############################################################################################################################################################################################################################################################################ 
################################################ Invoice Note Functions ################################################################################################################################################################
###################################################################################################################################################################################################################################################################################

    # Recieves the type of reminder (Daily / Weekly), the invoice id, the email address and the content of the email
    
    def invoice_reminder_note(self, type, invoice, email, content):
        date = datetime.now().date()
        notes = f'''
            <div>
                <br>
                <h2 style="font-family:Arial;">
                    {type} reminder e-mail sent to {email} on {date} with content:
                </h2>
                <br>
                <div style="background-color: #D6EBF0; color: #000000; padding: 20px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                    {content} 
                </div>
                <br>
            </div>
        '''
        invoice.message_post(body=notes)
    
    def calculate_product_inv(self, id):
        product_ids = self.env["account.move.line"].sudo().search([
            ("move_id", "=", id)
        ]).product_id.mapped("name")
        if product_ids:
            product_name = ','.join(product_ids)
            return product_name
        else:
            return False
    
    def send_daily_reminder(self):
        for record in self:
            template_id = None
            if record.company_id.name == "3rd Party":
                template_id = self.env.ref('pms.daily_3rdparty_unpaid_invoices_email_template').id
            else:
                template_id = self.env.ref('pms.daily_unpaid_invoices_email_template').id
            
            template = self.env['mail.template'].browse(template_id)

            email_addresses = [record.partner_id.email] if record.partner_id.email else []
            email_addresses.extend([child.email for child in record.partner_id.child_ids if child.email])
            email_to = ','.join(email_addresses)

            short_analytic_accounts = record.analytic_accounts
            
            product_inv = record.calculate_product_inv(record.id)
                
            if record.analytic_accounts:
                parts = record.analytic_accounts.split(',', 2)
                short_analytic_accounts = ','.join(parts[:2]) if len(parts) > 1 else record.analytic_accounts

            def split_properties(analytic_accounts):
                properties = []
                parts = analytic_accounts.split(',')
                i = 0
                while i < len(parts) - 1:
                    properties.append(f"{parts[i]},{parts[i+1]}")
                    i += 2
                return properties

            skip_email = False
            if record.analytic_accounts:
                properties = split_properties(record.analytic_accounts)
                for property_name in properties:
                    property_record = self.env['pms.property'].search([('analytical_account.name', '=', property_name)], limit=1)
                    if property_record:
                        project_record = self.env['pms.projects'].search([('address', '=', property_record.id)], limit=1)
                        if project_record and project_record.custodial_money:
                            skip_email = True
                            break

            if skip_email:
                continue

            if record.company_id.name != "3rd Party":
                report_action = self.env.ref('pms.account_invoices') 
                data_record = base64.b64encode(
                self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                report_action, [record.id], data=None)[0])

                ir_values = {
                    'name': 'Unpaid_Invoice_Report',
                    'type': 'binary',
                    'datas': data_record,
                    'store_fname': data_record,
                    'mimetype': 'application/pdf',
                    'res_model': 'account.move',
                }

                invoice_report_attachment_id = self.env[
                'ir.attachment'].sudo().create(
                ir_values)

                if invoice_report_attachment_id:
                    email_template = self.env.ref(
                    'pms.daily_unpaid_invoices_email_template')



                payment_link = f'{record.get_base_url()}{record.get_portal_url()}'
                html_content = f'''
                <h2 style="font-family:Arial;">
                    Querido {record.partner_id.name},
                </h2>
                <p style="font-family:Arial;">
                    Nos dirigimos a usted para recordarle que la factura #{record.name} 
                    por un monto de ${record.amount_total:,.2f}, se encuentra pendiente de pago.
                </p>
                <p style="font-family:Arial;">
                    Agradeceríamos mucho su pronta atención a este asunto, para que su propiedad no sea puesta en Hold. 
                    Si ya ha realizado el pago, por favor ignore este mensaje y le pedimos disculpas por cualquier inconveniente.
                </p>
                <p style="font-family:Arial;">
                    Agradecemos su colaboración y esperamos seguir trabajando juntos.
                </p>
                <a href="{payment_link}" style="
                                        display: inline-block;
                                        background-color: #000000;
                                        border: 2px solid #1A1A1A;
                                        border-radius: 12px;
                                        box-sizing: border-box;
                                        color: #FFFFFF;
                                        cursor: pointer;
                                        font-family: Arial;
                                        font-size: 12px;
                                        font-weight: 600;
                                        line-height: normal;
                                        margin: 6;
                                        min-height: 40px;
                                        outline: none;
                                        padding: 12px 18px;
                                        text-align: center;
                                        text-decoration: none;
                                        transition: all 300ms cubic-bezier(.23, 1, 0.32, 1);
                                        user-select: none;
                                        width: 20%;
                                        -webkit-user-select: none;
                                        touch-action: manipulation;
                                        will-change: transform;
                                    "><strong>PAY NOW</strong></a>
                '''

                if record.company_id and short_analytic_accounts and product_inv:
                    subject = f"{record.company_id.name} - {short_analytic_accounts} - {product_inv}"
                elif not product_inv and not short_analytic_accounts:
                    subject = f"Unpaid Invoices Notification: {record.company_id.name}"
                elif not short_analytic_accounts:
                    subject = f"{record.company_id.name} - {product_inv}"
                else:
                    subject = f"{record.company_id.name} - {short_analytic_accounts}"

                email_values = {
                    'email_to': email_to,
                    'email_from': self.env.user.email,
                    'subject': subject,
                    'body_html': html_content
                }

                email_template.attachment_ids = [(4, invoice_report_attachment_id.id)]
                email_template.send_mail(record.id, force_send=True, email_values=email_values)
                email_template.attachment_ids = [(5, 0, 0)]
                # self.env['mail.mail'].create(email_values).send()
                self.invoice_reminder_note("Daily", self.env['account.move'].browse(record.id), email_to, html_content)                
                
            else:
                html_content = f'''
                        <h2 style="font-family:Arial;">
                            Querido {record.partner_id.name},
                        </h2>
                        <p style="font-family:Arial;">
                            Nos dirigimos a usted para recordarle que la factura #{record.payment_reference} 
                            por un monto de ${record.amount_total:,.2f}, se encuentra pendiente de pago.
                        </p>
                        <p style="font-family:Arial;">
                            Agradeceríamos mucho su pronta atención a este asunto, 
                            para que su propiedad no sea puesta en Hold. Si ya ha realizado el pago, 
                            por favor ignore este mensaje y le pedimos disculpas por cualquier inconveniente.
                        </p>
                        <p style="font-family:Arial;">
                            Agradecemos su colaboración y esperamos seguir trabajando juntos.
                        </p>
                    '''

                if record.contractor and short_analytic_accounts and product_inv:
                    subject = f"{record.contractor.name} - {short_analytic_accounts} - {product_inv}"
                elif not product_inv and not short_analytic_accounts:
                    subject = f"Unpaid Invoices Notification: {record.contractor.name}"
                elif not record.contractor and not product_inv:
                    subject = f"Unpaid Invoices Notification: {short_analytic_accounts}"
                elif not short_analytic_accounts:
                    subject = f"{record.contractor.name} - {product_inv}"
                elif not record.contractor.name:
                    subject = f"{short_analytic_accounts} - {product_inv}"
                else:
                    subject = f"{record.contractor.name} - {short_analytic_accounts}"

                email_values = {
                    'email_to': email_to,
                    'email_from': self.env.user.email,
                    'subject': subject,
                    'body_html': html_content
                }

                template.send_mail(record.id, force_send=True, email_values=email_values)
                self.invoice_reminder_note("Daily", self.env['account.move'].browse(record.id), email_to, html_content)                
    

    def send_unpaid_invoices_email_weekly(self):
        customers = self.env['res.partner'].search([])
        max_date = datetime.now().date()

        for customer in customers:
            invoices = self.search([('partner_id', '=', customer.id), 
                                    ('payment_state', '=', 'not_paid'), 
                                    ('move_type', '=', 'out_invoice'),
                                    ('state', '=', 'posted'), 
                                    ('invoice_date_due', '<', max_date),])
            if not invoices:
                continue

            grouped_invoices = defaultdict(list)
            for invoice in invoices:
                property_name = 'Unknown Property or more than one property in a single invoice.'
                if invoice.analytic_accounts:
                    analytic_account = invoice.analytic_accounts
                    property_record = self.env['pms.property'].search([('analytical_account.name', '=', analytic_account)], limit=1)
                    if property_record:
                        property_name = property_record.name
                        project = self.env['pms.projects'].search([('address', '=', property_record.id), ('custodial_money', '=', False)], limit=1)
                        if not project:
                            continue 

                grouped_invoices[property_name].append(invoice)

            if not grouped_invoices:
                continue
            
            html_content = f'''
                <h2 style="font-family:Arial;">
                    Querido {customer.name},
                </h2>
                <p style="font-family:Arial;">
                    Nos dirigimos a usted para recordarle que tiene facturas que se encuentran pendientes de pago.
                </p>
                <p style="font-family:Arial;">
                    Agradeceríamos mucho su pronta atención a este asunto, para que sus propiedades no sean puestas en Hold. 
                    Si ya ha realizado el pago, por favor ignore este mensaje y le pedimos disculpas por cualquier inconveniente.
                </p>
                <p style="font-family:Arial;">
                    Agradecemos su colaboración y esperamos seguir trabajando juntos.
                </p>
            '''      
            html_content += f'<h2 style="font-family:Arial;">Unpaid Invoices for {customer.name}</h2>'
            overall_total = 0
            for property_name, invoices in grouped_invoices.items():
                html_content += f'<h3 style="font-family:Arial;">{property_name}</h3>'
                html_content += '''
                    <table border="1" style="width:100%; border-collapse: collapse;">
                        <tr>
                            <th><a style="font-family:Arial;">
                                Invoice Number
                            </a></th>
                            <th><a style="font-family:Arial;">
                                Invoice Reference
                            </a></th>
                            <th><a style="font-family:Arial;">
                                Due Date
                            </a></th>
                            <th><a style="font-family:Arial;">
                                Amount
                            </a></th>
                            <th><a style="font-family:Arial;">
                                Payment Link
                            </a></th>
                        </tr>
                '''
                property_total = 0
                for invoice in invoices:
                    if invoice.company_id.name == '3rd Party':
                        if invoice.invoice_link_docs:
                            html_content += f'''
                                <tr>
                                    <td> </td>
                                    <td><a style="font-family:Arial;">
                                        {invoice.payment_reference}
                                    </a></td>
                                    <td><a style="font-family:Arial;">
                                        {invoice.invoice_date_due}
                                    </a></td>
                                    <td><a style="font-family:Arial;">
                                        ${invoice.amount_total:,.2f}
                                    </a></td>
                                    <td colspan="4" style="text-align:center;">
                                        <a href="{invoice.invoice_link_docs}" style="
                                            display: inline-block;
                                            background-color: #000000;
                                            border: 2px solid #1A1A1A;
                                            border-radius: 12px;
                                            box-sizing: border-box;
                                            color: #FFFFFF;
                                            cursor: pointer;
                                            font-family: Arial;
                                            font-size: 12px;
                                            font-weight: 600;
                                            line-height: normal;
                                            margin: 6;
                                            min-height: 40px;
                                            outline: none;
                                            padding: 12px 18px;
                                            text-align: center;
                                            text-decoration: none;
                                            transition: all 300ms cubic-bezier(.23, 1, 0.32, 1);
                                            user-select: none;
                                            width: 80%;
                                            -webkit-user-select: none;
                                            touch-action: manipulation;
                                            will-change: transform;
                                        "><strong>PAY NOW</strong></a>
                                    </td>
                                </tr>
                            '''
                            property_total += invoice.amount_total
                        else:
                            html_content += f'''
                                <tr>
                                    <td></td>
                                    <td><a style="font-family:Arial;">
                                        {invoice.payment_reference}
                                    </a></td>
                                    <td><a style="font-family:Arial;">
                                        {invoice.invoice_date_due}
                                    </a></td>
                                    <td><a style="font-family:Arial;">
                                        ${invoice.amount_total:,.2f}
                                    </a></td>
                                    <td></td>
                                </tr>
                            '''
                            property_total += invoice.amount_total
                    else:
                        payment_link = f'{invoice.get_base_url()}{invoice.get_portal_url()}'
                        html_content += f'''
                            <tr>
                                <td><a style="font-family:Arial;">{invoice.name}</a></td>
                                <td><a style="font-family:Arial;">{invoice.payment_reference}</a></td>
                                <td><a style="font-family:Arial;">{invoice.invoice_date_due}</a></td>
                                <td><a style="font-family:Arial;">${invoice.amount_total:,.2f}</a></td>
                                <td colspan="4" style="text-align:center;">
                                    <a href="{payment_link}" style="
                                        display: inline-block;
                                        background-color: #000000;
                                        border: 2px solid #1A1A1A;
                                        border-radius: 12px;
                                        box-sizing: border-box;
                                        color: #FFFFFF;
                                        cursor: pointer;
                                        font-family: Arial;
                                        font-size: 12px;
                                        font-weight: 600;
                                        line-height: normal;
                                        margin: 6;
                                        min-height: 40px;
                                        outline: none;
                                        padding: 12px 18px;
                                        text-align: center;
                                        text-decoration: none;
                                        transition: all 300ms cubic-bezier(.23, 1, 0.32, 1);
                                        user-select: none;
                                        width: 80%;
                                        -webkit-user-select: none;
                                        touch-action: manipulation;
                                        will-change: transform;
                                    "><strong>PAY NOW</strong></a>
                                </td>
                            </tr>
                        '''
                        property_total += invoice.amount_total
                html_content += f'''
                        <tr>
                            <td colspan="3"><strong style="font-family:Arial;">
                                PROPERTY TOTAL
                            </strong></td>
                            <td><strong style="font-family:Arial;">
                                ${property_total:,.2f}
                            </strong></td>
                        </tr>
                    </table>
                '''
                overall_total += property_total

            html_content += f'<h3 style="font-family:Arial;">Overall Total: ${overall_total:,.2f}</h3>'

            email_addresses = [customer.email] if customer.email else []
            email_addresses.extend([child.email for child in customer.child_ids if child.email])

            email_to = ','.join(email_addresses)

            if email_to:
                mail_values = {
                    'subject': f'Unpaid Invoices Notification: {customer.name}',
                    'body_html': html_content,
                    'email_to': email_to,
                }
                self.env['mail.mail'].create(mail_values).send()
                
                # Sends email copy to internal notes
                
                invoice = self.env['account.move'].browse(invoice.id)
                self.invoice_reminder_note("Weekly", invoice, email_to, html_content)

###################################################################################################################################################################################################################################################################################

###################################################################################################################################################################################################################################################################################

   


    @api.onchange('linked_material_order')
    def _onchange_linked_material_order(self):
        if self.linked_material_order:
            self.linked_material_order.has_bill = True

    @api.depends("linked_material_order")
    def send_bill_id(self):
        if self.linked_material_order:
            order = self.env["pms.materials"].search([("id", "=", self.linked_material_order.id)])
            order.bill_id = self.id

    def open_linked_material_order(self):
        self.ensure_one()
        return {
        'type': 'ir.actions.act_window',
        'name': ('pms_materials_view_form'),
        'res_model': 'pms.materials',
        'res_id': self.linked_material_order.id,
        'view_mode': 'form'}


    @api.onchange("date")
    def _onchange_invoice_date(self):
        for record in self:
            record.budget_date = record.date

    def open_mail_messages(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mail Messages',
            'view_mode': 'tree,form',
            'res_model': 'mail.message',
            'views': [
                (self.env.ref('prt_mail_messages.prt_mail_message_tree').id, 'tree'),
                (self.env.ref('prt_mail_messages.prt_mail_message_form').id, 'form')
            ],
            'domain': [('model', '=', 'account.move'), ('res_id', '=', self.id)],
            'target': 'current',
        }

    def action_open_invoiced_report(self):
        self.ensure_one()
        return {
            'name': self.invoiced.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoiced.id
        }

    def action_open_billables_report(self):
        self.ensure_one()
        return {
            'name': self.billables.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.billables.id
        }
        

    def action_post(self):
        moves_with_payments = self.filtered('payment_id')
        other_moves = self - moves_with_payments

        for move in self:
            _logger.info(f"Processing move: {move.name}, type: {move.move_type}, payment_type_bills: {move.payment_type_bills}, employee: {move.employee_id}")

            if move.move_type == "out_invoice":
                # Generate Link url for email invoicing with it
                url = move.get_portal_url()

                lines = move.line_ids

                if lines:
                    for analytic_id in lines:
                        analytic_i = analytic_id.analytic_distribution
                        if analytic_i:
                            for key in analytic_i.keys():
                                address = self.env["pms.property"].sudo().search([("analytical_account", "=", int(key))], limit=1)
                                if address:
                                    project = self.env["pms.projects"].sudo().search([("address", "=", address.id)])
                                    _logger.info(project)
                                    if project.status_construction in ["coc", "completed"]:
                                        self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                                            'type': 'danger',
                                            'title': _("Warning"),
                                            'message': ('This property is in status COC please check')
                                        })

            # LOGIC MOVED TO APPROVED.BILLS
            
            # if move.payment_type_bills == "online" and move.move_type == "in_invoice":
            #     _logger.info(f"Payment request conditions met for move: {move.name}")
            #     if move.employee_id == False:
            #         raise UserError(_("You must select an employee to process the payment"))
            #     else:
            #         _logger.info(f"Calling request_payment for move: {move.name}")
            #         move.request_payment()
            # else:
            #     _logger.info(f"Payment request conditions NOT met for move: {move.name}")

        if moves_with_payments:
            pass
            # moves_with_payments.payment_id.action_post()
        if other_moves:
            other_moves._post(soft=False)

        closing_check_lol = self.closing_check()

        if any(self.line_ids.mapped("billable")):
            if self.move_type in ("out_invoice", "out_refund"):
                raise UserError(_("You cannot post an invoice with billable lines"))

            new_entry = self._create_billable_entries()
            if new_entry:
                self.line_ids.filtered(lambda x: x.billable == True).invoiced = new_entry.id
                new_entry.billables = self.id
                self.invoiced = new_entry.id

        return False
    
# Checking property and product in the invoice lines
    def closing_check(self):
        for move in self:
            all_lines = move.line_ids
            if all_lines:
                address_final = []
                all_lines = all_lines.filtered_domain(["&", ("analytic_distribution", "!=", False), ("account_id.code", "=", "1000201")])
                for analytic_id in all_lines:
                    analytic_i = analytic_id.analytic_distribution
                    if analytic_i:
                        for key in analytic_i.keys():
                            address = move.env["account.analytic.account"].sudo().search([("id", "=", key)]).id
                            address_final.append(address)
                
                # look if address in pms has check in closure
                pms_address = move.env["pms.property"].sudo().search([("analytical_account", "in", address_final)])
                if pms_address:
                    closing_check = pms_address.mapped("residential_unit_closure")
                    if True in closing_check:
                        raise UserError(_("Some of the properties in the journal entry have already been closed you cant change them please contact your administrator to know how to do proceed"))
                return True


    def bill_check(self):
        for move in self:
            if move.move_type == "out_invoice" and move.lock_on_coc and not move.coc_approved:
                self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'danger',
                    'title': _("Warning"),
                    'message': ('This property is in status COC please request approval before confirming.')
                })
                continue
            if move.move_type == "in_invoice":
                all_bills = move.line_ids
                if all_bills:
                    address_final = []
                    price_exceeded = []
                    
                    for analytic_id in all_bills:
                        price_check = analytic_id.product_id.max_price
                        if analytic_id.price_subtotal > price_check:
                            price_exceeded.append(f'{analytic_id.product_id.name} - ${price_check}')
                        
                        analytic_i = analytic_id.analytic_distribution
                        if analytic_i:
                            for key in analytic_i.keys():
                                address = move.env["account.analytic.account"].sudo().search([("id", "=", key)]).id
                                address_final.append(address)

                    dup = move.env["account.analytic.line"].search([
                        "&",
                        ("product_id", "in", all_bills.mapped("product_id.id")),
                        "&",
                        ("account_id", "in", address_final),
                        ("category", "=", "vendor_bill")  
                    ])

                    bill_lines_grouped = {}
                    for bill_line in all_bills:
                        if isinstance(bill_line.analytic_distribution, dict):
                            analytic_keys = list(bill_line.analytic_distribution.keys())
                            if not analytic_keys:
                                continue

                            analytic_account_id = analytic_keys[0]
                            property_record = self.env["pms.property"].sudo().search([
                                ('analytical_account', '=', int(analytic_account_id))
                            ], limit=1)

                            if not property_record:
                                continue

                            house_model_id = property_record.house_model.id
                            city = property_record.city.id
                            
                            group_key = (bill_line.product_id.id, analytic_account_id, house_model_id, city)
                            if group_key not in bill_lines_grouped:
                                bill_lines_grouped[group_key] = 0
                            bill_lines_grouped[group_key] += bill_line.price_subtotal

                    budget_exceeded = []

                    for (product_id, analytic_account_id, house_model_id, city), bill_total in bill_lines_grouped.items():
                        budget_domain = [
                            ('product_model', '=', product_id),
                            ('house_model', '=', house_model_id),
                            ('city', '=', city)  
                        ]
                        
                        budget_line = self.env['budget.model'].sudo().search(budget_domain)

                        if not budget_line:
                            budget_domain = [
                                ('product_model', '=', product_id),
                                ('house_model', '=', house_model_id),
                                ('city', '=', False) 
                            ]
                            budget_line = self.env['budget.model'].sudo().search(budget_domain)

                        if not budget_line:
                            budget_domain = [
                                ('product_model', '=', product_id),
                                ('house_model', '=', house_model_id),
                            ]
                            budget_line = self.env['budget.model'].sudo().search(budget_domain)

                        budget_amount = 0.0

                        analytic_lines = self.env['account.analytic.line'].sudo().search([
                            ('product_id', '=', product_id),
                            ('account_id', '=', int(analytic_account_id)),
                            ('move_line_id.move_id.move_type', '=', 'in_invoice')
                        ])

                        for bill_line in all_bills:
                            if not bill_line.product_id:
                                continue

                            if bill_line.activity in budget_line.mapped('activity'):
                                if move.partner_id in budget_line.mapped('supplier'):
                                    budget_line_activity = budget_line.filtered_domain([
                                        ('activity', '=', bill_line.activity.id),
                                        ('supplier', '=', move.partner_id.id)
                                    ])
                                    if budget_line_activity:
                                        budget_amount = abs(sum(budget_line_activity.mapped('amount')))
                                else:
                                    budget_line_activity = budget_line.filtered_domain([
                                        ('activity', '=', bill_line.activity.id)
                                    ])
                                    if budget_line_activity:
                                        budget_amount = abs(sum(budget_line_activity.mapped('amount')))
                            else:
                                if move.partner_id in budget_line.mapped('supplier'):
                                    budget_line_partner = budget_line.filtered_domain([('supplier', '=', move.partner_id.id)])
                                    if budget_line_partner:
                                        budget_amount = abs(sum(budget_line_partner.mapped('amount')))
                                else:
                                    budget_amount = abs(sum(budget_line.mapped('amount')))

                            total_amount = abs(sum(analytic_lines.mapped('amount'))) + abs(bill_total)

                            if budget_line and total_amount > budget_amount:
                                budget_exceeded.append(f'{self.env["product.product"].browse(product_id).name} - Budget: ${budget_amount}, Spent: ${total_amount}')


                    if budget_exceeded:
                        budget_exceeded_list = "\n".join(budget_exceeded)
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'Budget Wizard',
                            'res_model': 'budget.check.wizard',
                            'view_mode': 'form',
                            'view_id': self.env.ref('pms.budget_check_wizard_form').id,
                            'target': 'new',
                            'context': {
                                'budget_text': budget_exceeded_list,
                                'bill_id': move.id
                            }
                        }
                    
                    if dup:
                        move.bill_alert = True
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'Bill Wizard',
                            'res_model': 'account.bill.wizard',
                            'view_mode': 'form',
                            'view_id': self.env.ref('pms.view_account_bill_wizard_form').id,
                            'target': 'new',
                            'context': {
                                'dup_id': move.id,
                                'bill_ids': dup.move_line_id.mapped("move_id.id")
                            }
                        }
                    else:
                        move.action_post()
            else:
                move.action_post()




    def _create_billable_entries(self):
        self.ensure_one()
        def_markup = self.env['ir.config_parameter'].sudo().get_param('pms.markup')

        lines = self.line_ids.filtered_domain(["&", ("billable", "=", True), ("invoiced", "=", False)])

        if lines:
                address_final = []
                for analytic_id in lines:
                    analytic_i = analytic_id.analytic_distribution
                    if analytic_i:
                        for key in analytic_i.keys():
                            address = self.env["pms.property"].sudo().search([("analytical_account", "=", int(key))])
                            address_final.append(address)
            
                address_final = list(set(address_final))
                if len(address_final) > 1:
                    for x in address_final:
                        if x.partner_id:
                            inv_customer = x.partner_id.id
                            property = x.analytical_account.id
                            entry_header = {
                            "move_type": "out_invoice",
                            "invoice_date": self.invoice_date,
                            "date": self.invoice_date,
                            "partner_id": inv_customer,
                            "invoice_origin": self.name,
                            "payment_reference": self.name
                        }

                            entry_lines = []
                        for line in lines:
                            analytic_i = line.analytic_distribution
                            if analytic_i:
                                for key in analytic_i.keys():
                                    address_line = self.env["account.analytic.account"].sudo().search([("id", "=", key)]).id
                                    property_line = self.env["pms.property"].sudo().search([("analytical_account", "=", address_line)])
                            
                                if property_line.id == x.id:
                                    
                                    if line.product_id:
                                        product = line.product_id.id
                                        if line.price_unit != 0.0:
                                            price = line.price_unit
                                        else:
                                            price = line.debit
                                        markup_amount = price * (float(line.markup) / 100)
                                        price = price + markup_amount
                                        entry_lines.append((0, 0, {
                                            "product_id": product,
                                            "price_unit": price,
                                            "quantity": line.quantity,
                                            "name": line.name,
                                            "analytic_distribution": {str(property):100.0}
                                        }))
                                    elif line.account_id:
                                        account = line.account_id
                                        if line.price_unit != 0.0:
                                            price = line.price_unit
                                        else:
                                            price = line.debit
                                        markup_amount = price * (float(line.markup) / 100)
                                        price = price + markup_amount
                                        entry_lines.append((0, 0, {
                                            "account_id": account.id,
                                            "price_unit": price,
                                            "quantity": line.quantity,
                                            "name": line.name,
                                            "analytic_distribution": {str(property):100.0}
                                        }))
                        entry_header["invoice_line_ids"] = entry_lines

                        entry = self.env["account.move"].create(entry_header)
                    return entry


                elif len(address_final) < 1:
                    raise UserError(_("Please set the property in the invoice lines"))
                else:
                    inv_customer = address_final[0].partner_id.id
                    property = address_final[0].analytical_account.id

        else:
            return False            
            

        if not def_markup:
            raise UserError(_("Please set the default markup in the settings"))
        


        entry_header = {
            "move_type": "out_invoice",
            "invoice_date": self.invoice_date,
            "date": self.invoice_date,
            "partner_id": inv_customer,
            "invoice_origin": self.name,
            "payment_reference": self.name
        }

        entry_lines = []


        for line in lines:

            if line.product_id:
                product = line.product_id.id
                if line.price_unit != 0.0:
                    price = line.price_unit
                else:
                    price = line.debit
                markup_amount = price * (float(line.markup) / 100)
                price = price + markup_amount
                entry_lines.append((0, 0, {
                    "product_id": product,
                    "price_unit": price,
                    "quantity": line.quantity,
                    "name": line.name,
                    "analytic_distribution": {str(property):100.0}
                }))
            elif line.account_id:
                account = line.account_id
                if line.price_unit != 0.0:
                    price = line.price_unit
                else:
                    price = line.debit
                markup_amount = price * (float(line.markup) / 100)
                price = price + markup_amount
                entry_lines.append((0, 0, {
                    "account_id": account.id,
                    "price_unit": price,
                    "quantity": line.quantity,
                    "name": line.name,
                    "analytic_distribution": {str(property):100.0}
                }))


        entry_header["invoice_line_ids"] = entry_lines

        entry = self.env["account.move"].create(entry_header)

        return entry

    

