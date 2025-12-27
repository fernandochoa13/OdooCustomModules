from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date, formatLang

# Includes Inherit Classes for: AccountPayment, AccountPaymentRegister, AccountPaymentTerm

class AccountPayment(models.Model):
    _inherit = ["account.payment"]

    delivery_date = fields.Date(string="Delivery Date", store=True, readonly=False)
    can_reconcile = fields.Boolean(
        string="Can Reconcile",
        compute="_compute_can_reconcile",
        help="Indicates if this payment can be reconciled (bank or cash journal)"
    )
    
    @api.depends('state', 'journal_id', 'journal_id.type')
    def _compute_can_reconcile(self):
        """Compute if the payment can be reconciled (only for posted payments with bank, cash, or credit card journals)."""
        for payment in self:
            payment.can_reconcile = (
                payment.state == 'posted' and
                payment.journal_id and
                payment.journal_id.type in ('bank', 'cash', 'general')
            )
    
    def _get_related_bills(self):
        """Get vendor bills related to this payment"""
        self.ensure_one()
        bills = self.env['account.move']
        
        # Only process vendor payments (supplier bills)
        if self.partner_type != 'supplier':
            return bills
        
        # Get bills from reconciled invoice lines
        if self.move_id and self.move_id.line_ids:
            payment_lines = self.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type == 'liability_payable'
            )
            
            for line in payment_lines:
                # Get matched debit lines (when we pay, we debit the payable account)
                # The credit side of the reconciliation is the bill's payable line
                if line.matched_credit_ids:
                    for matched in line.matched_credit_ids:
                        bill = matched.credit_move_id.move_id
                        if bill.move_type == 'in_invoice' and bill not in bills:
                            bills |= bill
                
                # Also check matched debit (for refunds or other cases)
                if line.matched_debit_ids:
                    for matched in line.matched_debit_ids:
                        bill = matched.debit_move_id.move_id
                        if bill.move_type == 'in_invoice' and bill not in bills:
                            bills |= bill
        
        return bills
    
    def _log_payment_details_to_bills(self):
        """Log payment details to the message history of related vendor bills"""
        for payment in self:
            # Only log for vendor payments (supplier bills)
            if payment.partner_type != 'supplier':
                continue
            
            bills = payment._get_related_bills()
            
            if not bills:
                continue
            
            # Prepare payment details
            payment_date = format_date(self.env, payment.date) if payment.date else 'N/A'
            payment_amount = formatLang(self.env, payment.amount, currency_obj=payment.currency_id) if payment.amount else 'N/A'
            payment_ref = payment.ref or payment.payment_reference or 'N/A'
            check_number = getattr(payment, 'check_number', False) or 'N/A'
            
            # Get the human-readable state label safely
            try:
                payment_state = dict(payment._fields['state']._description_selection(self.env)).get(payment.state, payment.state)
            except (AttributeError, KeyError):
                payment_state = payment.state.title() if payment.state else 'N/A'
            
            # Create HTML message
            message_body = f"""
                <div style="background-color: #D6EBF0; color: #000000; padding: 15px; margin: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                    <h3 style="margin-top: 0; color: #007bff;"><b>Payment Details</b></h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 5px; font-weight: bold; width: 40%;">Payment Date:</td>
                            <td style="padding: 5px;">{payment_date}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; font-weight: bold;">Amount:</td>
                            <td style="padding: 5px;">{payment_amount}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; font-weight: bold;">Memo/Reference:</td>
                            <td style="padding: 5px;">{payment_ref}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; font-weight: bold;">Check Number:</td>
                            <td style="padding: 5px;">{check_number}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; font-weight: bold;">Payment Status:</td>
                            <td style="padding: 5px;">{payment_state}</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; font-weight: bold;">Payment Number:</td>
                            <td style="padding: 5px;">{payment.name or 'N/A'}</td>
                        </tr>
                    </table>
                </div>
            """
            
            # Post message to each related bill
            for bill in bills:
                bill.message_post(
                    body=message_body,
                    subject=f"Payment Details - {payment.name or 'Payment'}",
                    message_type='notification'
                )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to log payment details to related bills"""
        payments = super(AccountPayment, self).create(vals_list)
        
        # Log payment details after creation if payment is posted
        # Note: Bills might not be reconciled yet at creation time
        for payment in payments:
            if payment.state == 'posted':
                payment._log_payment_details_to_bills()
        
        return payments
    
    def write(self, vals):
        """Override write to log payment details when payment is modified"""
        # Store old state to detect state changes
        old_states = {payment.id: payment.state for payment in self}
        
        result = super(AccountPayment, self).write(vals)
        
        # Log payment details if:
        # 1. State changed to 'posted'
        # 2. Payment date, amount, ref, or check_number changed (and payment is posted)
        # 3. After write, check if payment is posted and has related bills (for reconciliation cases)
        
        fields_to_track = ['date', 'amount', 'ref', 'payment_reference', 'check_number', 'state']
        should_log = any(field in vals for field in fields_to_track)
        
        for payment in self:
            # Log if state changed to posted
            state_changed_to_posted = (
                'state' in vals and 
                old_states.get(payment.id) != 'posted' and 
                payment.state == 'posted'
            )
            
            # Log if payment details changed and payment is posted
            details_changed = (
                should_log and 
                payment.state == 'posted' and
                any(field in vals for field in ['date', 'amount', 'ref', 'payment_reference', 'check_number'])
            )
            
            # Check if payment is posted and has bills (catches reconciliation after posting)
            if state_changed_to_posted or details_changed:
                bills = payment._get_related_bills()
                if bills:
                    payment._log_payment_details_to_bills()
        
        return result

    @api.constrains("ref", "payment_method_line_id")
    def _check_ref(self):
        for payment in self:
            if not payment.ref and payment.payment_method_code == "new_ach_fast_payment":
                raise ValidationError(_("Payments require a memo"))

    @api.model
    def _get_method_codes_using_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_using_bank_account()
        res.append('new_ach_fast_payment')
        return res

    @api.model
    def _get_method_codes_needing_bank_account(self):
        res = super(AccountPayment, self)._get_method_codes_needing_bank_account()
        res.append('new_ach_fast_payment')
        return res

    def action_post(self):
        """Override action_post to log payment details when payment is posted"""
        result = super(AccountPayment, self).action_post()
        
        # Log payment details after posting
        for payment in self:
            if payment.partner_type == 'supplier':
                payment._log_payment_details_to_bills()
        
        return result
    
    def action_open_reconcile(self):
        """Open the bank reconciliation widget for bank, cash, and credit card journal payments."""
        self.ensure_one()
        
        if not self.journal_id:
            raise ValidationError(_("No journal is set on this payment."))
        
        if self.journal_id.type not in ('bank', 'cash', 'general'):
            raise ValidationError(_("Reconciliation is only available for bank, cash, and credit card journals."))
        
        if self.state != 'posted':
            raise ValidationError(_("Only posted payments can be reconciled."))
        
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            default_context={
                'default_journal_id': self.journal_id.id,
                'search_default_journal_id': self.journal_id.id,
                'search_default_not_matched': True,
            },
        ) 


    class AccountPaymentRegister(models.TransientModel):
        _inherit = 'account.payment.register'

        analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')

        def _post_payments(self, to_process, edit_mode=False):
            """ Post the newly created payments.

            :param to_process:  A list of python dictionary, one for each payment to create, containing:
                                * create_vals:  The values used for the 'create' method.
                                * to_reconcile: The journal items to perform the reconciliation.
                                * batch:        A python dict containing everything you want about the source journal items
                                                to which a payment will be created (see '_get_batches').
            :param edit_mode:   Is the wizard in edition mode.
            """

            payments = self.env['account.payment']
            for vals in to_process:
                # Modify the payment creation values to add the analytic account
                if self.analytic_account_id:
                    ar = vals['to_reconcile'][0]
                    move = ar.move_id
                    products = move.line_ids.filtered(lambda l: l.display_type == 'product').product_id
                            

                    payment_id = vals['payment']
                    if len(products.ids) == 1:
                        payment_id.move_id.line_ids.write({
                            'analytic_distribution': {str(self.analytic_account_id.id):100.00},
                            'product_id': products.id
                        })
                    else:
                         payment_id.move_id.line_ids.write({
                            'analytic_distribution': {str(self.analytic_account_id.id):100.00}
                        })

                payments |= vals['payment']
            payments.action_post()


    
class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    anticipated_payment = fields.Boolean(string='Anticipated Payment', default=False)
    utility_payment = fields.Boolean("Utility Payment", default=False)
    material_payment = fields.Boolean("Material Payment", default=False)