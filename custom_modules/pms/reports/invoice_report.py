from odoo import models, fields, tools, _, api
from odoo.exceptions import ValidationError, UserError

import re
import logging
_logger = logging.getLogger(__name__)

class invoice_report(models.Model):
    _name = "invoice.report"
    _description = "Invoice Report"
    _auto = False
    
    id = fields.Integer(string="id", readonly=True)
    
    res_model = fields.Char(string="Model", readonly=True)
    res_id = fields.Integer(string="ID", readonly=True)
    
    invoice_id = fields.Many2one('account.move', string="Invoice ID", readonly=True)
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', readonly=True)
    name = fields.Char(readonly=True, string="Number")
    invoice_partner_display_name = fields.Char(readonly=True, string="Customer")
    invoice_date = fields.Date(readonly=True, string="Invoice/Bill Date")
    invoice_date_due = fields.Date(string='Due Date', readonly=True)    
    date_paid = fields.Date(string="Date Paid", readonly=True)
    payment_state = fields.Selection(readonly=True, string="Payment Status", selection=[
            ('not_paid', 'Not Paid'), ('in_payment', 'In Payment'), ('paid', 'Paid'), ('partial', 'Partially Paid'),
            ('reversed', 'Reversed'), ('invoicing_legacy', 'Invoicing App Legacy'),
        ])
    state = fields.Selection(string='Status', readonly=True, selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ])
#    to_check = fields.Boolean(
#        string='To Check',
 #       readonly=True,
  #      help="If this checkbox is ticked, it means that the user was not sure of all the related "
   #          "information at the time of the creation of the move and that the move needs to be "
    #         "checked again.",
   # )
    # Custom fields
    contractor = fields.Many2one("res.partner", string="Contractor")
    activity_completed = fields.Boolean(string="Activity Completed", readonly=True)
    salesperson = fields.Many2one('res.users', string="Salesperson", readonly=True)
    bill_alert = fields.Boolean(string="Bill Alert", readonly=True)
    
    
    invoice_type = fields.Selection(readonly=True, string="Invoice Type", selection=[
            ("3rdparty", "3rd Party"), ("hold", "On Hold"), ("1stparty", "1st Party"), 
            ("escrow", "Escrow Money"), ("various", "Various")
        ])
    note_inv = fields.Text(readonly=True, string="Note" )
    last_customer_message = fields.Html(readonly=True, string="Last Customer Message")
    # house_model = fields.Char(readonly=True, string="House Model")
    # on_hold_comments = fields.Text(readonly=True, string="On Hold Comments") 
    
    # HTML
    analytic_accounts = fields.Char(readonly=True, string="Analytic Account (String)")
    analytic_accounts_html = fields.Html(readonly=True, string="Analytic Account (HTML)", compute="_compute_analytic_accs_html")
    product_inv = fields.Char(readonly=True, string="Product (String)")
    product_inv_html = fields.Html(readonly=True, string="Product (HTML)", compute="_compute_product_inv_html")
    
    # Hidden
    date = fields.Date(string='Accounting Date', readonly=True)
    invoice_origin = fields.Char(string='Origin', readonly=True)
    ref = fields.Char(string='Reference', readonly=True)

    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    # Floats
    amount_untaxed_signed = fields.Float(string='Tax Excluded', readonly=True)
    amount_total_signed = fields.Float(string='Total', readonly=True)
    amount_tax_signed = fields.Float(string='Tax', readonly=True)
    amount_residual_signed = fields.Float(string='Amount Due', readonly=True)

    # currency_id = fields.Many2one('res.currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')]).id, readonly=True)

    # Needed fields for functions
    move_type = fields.Selection(string='Type', readonly=True, default="entry", selection=[
            ('entry', 'Journal Entry'), ('out_invoice', 'Customer Invoice'), ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'), ('in_refund', 'Vendor Credit Note'), ('out_receipt', 'Sales Receipt'), ('in_receipt', 'Purchase Receipt'),
        ])
    
    invoice_user_id = fields.Many2one(
        string='User',
        comodel_name='res.users',
        default=lambda self: self.env.user,
    )
    invoice_category = fields.Selection(string="Invoice Category", readonly=True,
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
    house_model = fields.Many2one("pms.housemodels", string="House Model")
    house_models = fields.Char(string="House Models", readonly=True, compute="_compute_house_models")
    completed_date = fields.Date(string="Completed Date")
    
    @api.depends("house_model", "invoice_id")
    def _compute_house_models(self):
        """Compute house models separated by comma from all properties linked to the invoice"""
        for record in self:
            if not record.invoice_id:
                record.house_models = ""
                continue
            
            # Get all house models from properties linked to this invoice
            house_models_list = []
            
            for line in record.invoice_id.line_ids:
                if line.analytic_distribution:
                    for analytic_id in line.analytic_distribution.keys():
                        property_obj = self.env['pms.property'].search([
                            ('analytical_account', '=', int(analytic_id))
                        ], limit=1)
                        if property_obj and property_obj.house_model:
                            model_name = property_obj.house_model.name
                            if model_name and model_name not in house_models_list:
                                house_models_list.append(model_name)
            
            record.house_models = ", ".join(house_models_list) if house_models_list else ""
    
    def view_update_payment_terms(self):
        selected_invoice_ids = self.env.context.get('active_ids', [])
        return {
            'name': 'Update Payment Terms',
            'view_mode': 'form',
            'res_model': 'update.payment.terms',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_invoice_ids': selected_invoice_ids,
                'default_show': False
            }
        }
        
        
    @api.depends("analytic_accounts")
    def _compute_analytic_accs_html(self):
        for record in self:
            if record.analytic_accounts:
                accounts = record.analytic_accounts.split(",")
                html_list = ""
                for account in accounts:
                    cleaned_account = account.strip()
                    if cleaned_account:
                        html_list += f"<div><i>{cleaned_account}</i></div>"
                record.analytic_accounts_html = html_list
            else:
                record.analytic_accounts_html = ""
    
    @api.depends("product_inv")
    def _compute_product_inv_html(self):
        for record in self:
            if record.product_inv:
                products = record.product_inv.split(",")
                html_string = ""
                for product in products:
                    # cleaned_product = product.strip()
                    if product:
                        html_string += f"""
                            <div style="display: inline-block; width: max-content; padding: 0px 5px; margin: 1px; border-radius: 20px; 
                                    border: 1.5px solid gray; background-color: white; color: gray">
                                <b>{product}</b>
                            </div>
                            <br>
                        """
                record.product_inv_html = html_string
            else:
                record.product_inv_html = ""
    
    def open_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'view_move_form',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.id
        }
        
    def new_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'view_move_form',
            'res_model': 'account.move',
            'view_mode': 'form',
        }
        
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
    
    def request_payment(self):
        property_ids = []
        invoice_line_ids = self.env['account.move.line'].search([('move_id', '=', self.id)])
        for line in invoice_line_ids:
            if line.analytic_distribution:
                analytic_account_ids = [int(analytic_id) for analytic_id in line.analytic_distribution.keys()]
                
                properties = self.env['pms.property'].search([
                    ('analytical_account', 'in', analytic_account_ids)
                ])
                
                property_ids.extend(properties.ids)
        
        property_ids = list(set(property_ids))
        
        record = self.env['cc.programmed.payment'].sudo().create({
            # 'requested_by': self.employee_id.id,
            # 'provider': self.partner_id.id,
            # 'amount': self.amount_total,
            'company': self.company_id.id,
            'request_date': fields.Date.today(),
            'payment_date': self.invoice_date_due,
            'concept': self.ref, # make sure this is ok
            'properties': [(6, 0, property_ids)], 
            'bill_id': self.id,
            'has_bill': True,
        })

        return {
            'name': 'Credit Card Programmed Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'cc.programmed.payment',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
        }
  
    def open_message_crm_wizard(self):
        for record in self:
            record = self.env['account.move'].browse(record.id)
            if not record.partner_id.email:
                raise ValidationError(_("Email field cannot be empty."))
            if not record.partner_id.phone and not record.partner_id.mobile:
                raise ValidationError(_("Either phone or mobile field must be filled."))

        wizard_view = self.env.ref('pms.view_message_crm_wizard_form')
        first_name = record.partner_id.display_name.split(' ')[0]
        last_name = record.partner_id.display_name.split(' ')[1]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'message.crm.wizard',
            'view_id': wizard_view.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': record.partner_id.id,
                'default_invoice_id': record.id,
                'default_contact_id': record.partner_id.contact_id if record.partner_id.contact_id else None,
                'default_first_name': first_name,
                'default_last_name': last_name,
                'default_email': record.partner_id.email,
                'default_phone_number': record.partner_id.phone or record.partner_id.mobile,
            },
        }
  
        
    def calculate_service_fee(self):
        for record in self:
            if record.move_type == 'out_invoice':
                if record.state == 'posted':
                    raise ValidationError("Service Fee can only be calculated for draft invoices.")
                else:
                    record = self.env['account.move'].browse(record.id)
                    for invoice_line in record.line_ids:
                        invoice_line.price_unit = invoice_line.price_unit + (record.service_fee * invoice_line.price_unit)
                    record.message_post(body="Service Fee Calculated")
            else:
                raise ValidationError("Service Fee can only be calculated for invoices.")

    def calculate_tax(self):
        for record in self:
            if record.move_type == 'out_invoice':
                if record.state == 'posted':
                    raise ValidationError("Tax can only be calculated for draft invoices.")
                else:
                    record = self.env['account.move'].browse(record.id)
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
    
    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        active_ids = self.env.context.get('active_ids', [])
        records = self.env['invoice.report'].browse(active_ids)
        invoices = records.mapped('invoice_id').ids
                
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': invoices,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
    
    def action_send_and_print(self):

        all_move_ids = self.env.context.get('active_ids')
        records = self.env['account.move'].browse(all_move_ids)

        if not records:
            raise UserError(_("No related invoices found for the selected records."))
        
        return {
            'name': _('Send Invoice'),
            'res_model': 'account.move.send',
            'view_mode': 'form',
            'context': {
                'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                'default_template_id': self.env.ref(self._get_mail_template()).id,
                'mark_invoice_as_sent': True,
                'active_model': 'account.move',
                'active_id': records.ids[0],
                'active_ids': records.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _get_mail_template(self):
        """
        :return: the correct mail template based on the current move type
        """
        return (
            'account.email_template_edi_credit_note'
            if all(move.move_type == 'out_refund' for move in self)
            else 'account.email_template_edi_invoice'
        )
        
    def init(self):
        tools.drop_view_if_exists(self._cr, 'invoice_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW invoice_report AS (
                SELECT
                    am.id AS id,
                    am.id as res_id, 
                    'account.move' as res_model,
                    am.id AS invoice_id,
                    am.name AS name,
                    am.completed_date AS completed_date,
                    am.move_type AS move_type,
                    am.invoice_filter_type AS invoice_category,
                    am.invoice_partner_display_name AS invoice_partner_display_name,
                    am.invoice_payment_term_id AS invoice_payment_term_id,
                    am.invoice_date AS invoice_date,
                    am.invoice_date_due AS invoice_date_due,
                    am.amount_untaxed_signed AS amount_untaxed_signed,
                    am.amount_total_signed AS amount_total_signed,
                    am.payment_state AS payment_state,
                    am.state AS state,
                    am.date AS date,
                    am.invoice_origin AS invoice_origin,
                    am.ref AS ref,
                    am.company_id AS company_id,
                    am.amount_tax_signed AS amount_tax_signed,
                    am.amount_residual_signed AS amount_residual_signed,
                    am.contractor AS contractor,
                    am.activity_completed AS activity_completed,
                    am.invoice_user_id AS salesperson,
                    am.invoice_user_id AS invoice_user_id,
                    am.bill_alert AS bill_alert,
                    (
                        SELECT DISTINCT
                            CASE
                                WHEN COUNT(DISTINCT pp.id) > 1 THEN 'various'
                                WHEN COUNT(DISTINCT pp.id) = 0 THEN NULL
                                WHEN BOOL_OR(pp.on_hold) = TRUE THEN 'hold'
                                WHEN BOOL_OR(pj.custodial_money) = TRUE THEN 'escrow'
                                WHEN BOOL_OR(rc.id IS NOT NULL) = TRUE AND BOOL_OR(pj.custodial_money) = FALSE THEN '1stparty'
                                ELSE '3rdparty'
                            END
                        FROM account_move_line AS aml
                        CROSS JOIN jsonb_each(aml.analytic_distribution) AS analytic_entry
                        INNER JOIN account_analytic_account AS aaa ON aaa.id = analytic_entry.key::int
                        LEFT JOIN pms_property AS pp ON pp.analytical_account = aaa.id
                        LEFT JOIN pms_projects AS pj ON pj.address = pp.id
                        LEFT JOIN res_company AS rc ON rc.partner_id = pp.partner_id
                        WHERE aml.move_id = am.id
                    ) AS invoice_type,
                    (
                        SELECT STRING_AGG(DISTINCT aaa.name::text, ',')
                        FROM account_move_line AS aml
                        CROSS JOIN jsonb_each(aml.analytic_distribution) AS analytic_entry  
                        INNER JOIN account_analytic_account AS aaa ON aaa.id = analytic_entry.key::int 
                        WHERE aml.move_id = am.id
                        GROUP BY aml.move_id  
                    ) AS analytic_accounts,
                    (
                        SELECT STRING_AGG(COALESCE(pt.name->>'en_US', pt.name::text), ', ')
                        FROM account_move_line AS aml
                        INNER JOIN product_product AS pp ON aml.product_id = pp.id
                        INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                        WHERE aml.move_id = am.id
                    ) AS product_inv,
                    COALESCE (
                        (
                            SELECT STRING_AGG(aml.name::text, ',')
                            FROM account_move_line AS aml
                            WHERE aml.move_id = am.id AND aml.display_type = 'line_section'
                        ),
                        (
                            SELECT STRING_AGG(aml.name::text, ',')
                            FROM account_move_line AS aml
                            WHERE aml.move_id = am.id AND aml.display_type = 'line_note'
                        ),
                        '' 
                    ) AS note_inv,
                    (
                        SELECT mm.body
                        FROM mail_message AS mm
                        WHERE
                            mm.model = 'account.move' AND
                            mm.res_id = am.id AND
                            mm.write_date >= CURRENT_DATE - INTERVAL '1 day'
                        ORDER BY mm.write_date DESC
                        LIMIT 1
                    ) AS last_customer_message,
                    am.date_paid AS date_paid,
                    (
                        SELECT MAX(pp.house_model)
                        FROM account_move_line AS aml
                        CROSS JOIN jsonb_each(aml.analytic_distribution) AS analytic_entry
                        INNER JOIN account_analytic_account AS aaa ON aaa.id = analytic_entry.key::int
                        LEFT JOIN pms_property AS pp ON pp.analytical_account = aaa.id
                        WHERE aml.move_id = am.id
                        AND pp.house_model IS NOT NULL
                    ) AS house_model
                FROM account_move am
                WHERE am.move_type = 'out_invoice'
                GROUP BY 
                    am.id, am.name, 
                    am.bill_alert, 
                    am.move_type, 
                    am.invoice_partner_display_name,
                    am.invoice_date,
                    am.invoice_date_due,
                    am.amount_untaxed_signed,
                    am.amount_total_signed,
                    am.payment_state,
                    am.state,
                    am.date,
                    am.invoice_origin,
                    am.ref,
                    am.company_id,
                    am.amount_tax_signed,
                    am.amount_residual_signed,
                    am.contractor,
                    am.activity_completed,
                    am.invoice_user_id,
                    am.invoice_user_id,
                    am.bill_alert
            )
        """)
        
                    # 'None' AS on_hold_comments
                    
                    
class update_payment_terms(models.TransientModel):
    _name = "update.payment.terms"
    _description = "Update Payment Terms"
    

    property_id = fields.Many2one('pms.property', string="Property")
    payment_terms_id = fields.Many2one('account.payment.term', string="Payment Terms")
    memo = fields.Text(string="Memo")

    show = fields.Boolean(string="Show", default=True)

    def update_invoice_payment_terms(self):
        _logger.info("Starting update_invoice_payment_terms wizard...")
        
        invoices_from_report = self.env.context.get('default_invoice_ids')
        invoices_updated_count = 0

        _logger.info(f"Context 'default_invoice_ids': {invoices_from_report}")

        if not invoices_from_report and not self.property_id:
            return self.env['update.owner.call.day'].simple_notification("error", "Error", "Unable to find any records to update.", False)

        if invoices_from_report and not self.property_id: # RUNS IF WIZARD WAS CALLED FROM REPORT
            _logger.info("Processing invoices from the report...")
            selected_invoices = self.env['account.move'].browse(invoices_from_report)
            if not selected_invoices:
                _logger.warning("No valid invoices found in the context.")
                return self.env['update.owner.call.day'].simple_notification("error", "Error", "Unable to find any records to update.", False)
            _logger.info(f"Invoices to update (from report): {selected_invoices.ids}")
            for invoice in selected_invoices:
                _logger.info(f"Updating payment term for invoice: {invoice.name} (ID: {invoice.id}) to {self.payment_terms_id.name}")
                invoice.invoice_payment_term_id = self.payment_terms_id.id
                notes = f'''
                    <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                        <b>Payment Terms Updated:</b><br>
                        <i>{self.memo}</i>
                    </div>
                '''
                invoice.message_post(body=notes)
                invoices_updated_count += 1

        elif self.property_id and not invoices_from_report: # RUNS IF WIZARD WAS CALLED FROM MENU
            _logger.info(f"Processing invoices based on property: {self.property_id.name} (ID: {self.property_id.id})...")
            _logger.info(f"Searching for move lines with analytic account ID: {self.property_id.analytical_account.id}")
            
            analytic_lines = self.env['account.analytic.line'].search([('account_id', '=', self.property_id.analytical_account.id)])

            
            if analytic_lines:
                moves = analytic_lines.move_line_id.mapped('move_id')
                _logger.info(f"Found moves with IDs: {moves}")
                _logger.info("Filtering invoices based on IDs, payment state, and status...")
                invoices_to_update = self.env['account.move'].search([
                    ('id', 'in', moves.ids),
                    ('payment_state', '=', 'not_paid'),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice'),
                ])
                
                if not invoices_to_update:
                    _logger.warning(f"No posted and unpaid customer invoices found for property: {self.property_id.name}.")
                    return self.env['update.owner.call.day'].simple_notification("error", "Error", f"No posted and unpaid customer invoices found for property: {self.property_id.name}.", False)
                _logger.info(f"Invoices to update (based on property): {invoices_to_update.ids}")
                
                for invoice in invoices_to_update:
                    _logger.info(f"Updating payment term for invoice: {invoice.name} (ID: {invoice.id}) to {self.payment_terms_id.name}")
                    invoice.invoice_payment_term_id = self.payment_terms_id.id
                    notes = f'''
                        <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                            <b>Payment Terms Updated:</b><br>
                            <i>{self.memo}</i>
                        </div>
                    '''
                    invoice.message_post(body=notes)
                    invoices_updated_count += 1
                    
            else:
                _logger.warning(f"No invoice lines found linked to the analytic account of property: {self.property_id.name}.")
                return self.env['update.owner.call.day'].simple_notification("error", "Error", f"No invoice lines found linked to the analytic account of property: {self.property_id.name}.", False)

        if invoices_updated_count > 0:
            _logger.info(f"Successfully updated {invoices_updated_count} invoices.")
            message = f"Successfully updated payment terms for {invoices_updated_count} invoice(s) to: {self.payment_terms_id.name}."
            notification_type = 'success'
                
        else:
            _logger.info("No invoices were updated.")
            message = "No invoices were updated."
            notification_type = 'info'

        return {
            'type': 'ir.actions.client', 
            'tag': 'display_notification',
            'params': {
                'message': message, 
                'type': notification_type, 
                'sticky': False, 
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }
