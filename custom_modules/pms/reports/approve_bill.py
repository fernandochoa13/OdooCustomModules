from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError

import logging
_logger = logging.getLogger(__name__)

# ENGINEERING FEE = SURVEY, PLOT PLANS, PLANS
# GC = GC
# PERMIT FEE = PERMITS PRODUCT

class ApproveBill(models.Model):
    _name = "approve.bills"
    _description = "Bills Report"
    _auto = False

    id = fields.Integer(readonly=True)
    partner = fields.Char(string='Partner', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    approved = fields.Boolean(string='Approved', readonly=True)
    amount_total = fields.Float(string='Total', readonly=True)
    amount_due = fields.Float(string='Amount Due', readonly=True)
    payment_reference = fields.Char(string='Payment Reference', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    company = fields.Char(string='Company', readonly=True)
    property_address = fields.Char(string='Property', readonly=True)
    linked_activities = fields.Many2one("pms.projects.routes", string="Linked Activity", readonly=True)
    activity_completed = fields.Boolean(string='Activity Completed', readonly=True)
    user_id = fields.Many2one("res.users", string='User', readonly=True)    
    county_name = fields.Char(string='County', readonly=True)
    
    # Account_move
    payment_type_bills = fields.Selection([("check", "Check"), ("online", "Online / CC"), ("material", "Material")], string="Payment Type", readonly=True)
    invoice_date = fields.Date(string="Invoice Date", readonly=True)
    product = fields.Char(string="Product")
    on_hold = fields.Boolean(string="On hold", readonly=True)
    price_estimate = fields.Float(string="Price estimate", readonly=True)
    price_difference = fields.Float(string="Price Difference", readonly=True)
    comments = fields.Char(string="Comments", readonly=True)
    priority = fields.Selection([('0', 'None'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority', readonly=True)
    
    invoice_date_due = fields.Date(string="Due Date", readonly=True)
    
    payment_state = fields.Char(string="Payment Status", readonly=True)

    def update_bill_user(self):
        _logger.info("update_user_priority method called")
        active_ids = self.env.context.get('active_ids', [])
        return {
            'name': 'Update Bill User Wizard',
            'view_mode': 'form',
            'res_model': 'update.bill.user.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'active_ids': active_ids},
        }

    def update_bill_priority(self):
        _logger.info("update_bill_priority method called")
        active_ids = self.env.context.get('active_ids', [])
        return {
            'name': 'Update Bill Wizard',
            'view_mode': 'form',
            'res_model': 'update.bill.priority.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'active_ids': active_ids},
        }

    def add_comment(self):
        return {
            'name': 'Add Comment Wizard',
            'view_mode': 'form',
            'res_model': 'add.approve.bills.comments',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def approve_bills(self):
        self.ensure_one()
        move = self.env['account.move'].browse(self.id)
        move.write({'approved': True})
        
        if move.payment_type_bills == "online" and move.move_type == "in_invoice":
            _logger.info(f"Payment request conditions met for move: {move.name}")
            if move.employee_id == False:
                raise UserError(_("You must select an employee to process the payment"))
            else:
                _logger.info(f"Calling request_payment for move: {move.name}")
                move.request_payment()
        else:
            _logger.info(f"Payment request conditions NOT met for move: {move.name}")

    def approve_bills_all(self):
        move_ids = self.mapped('id')
        moves = self.env['account.move'].browse(move_ids)
        moves.write({'approved': True})
        
        for move in moves:
            if move.payment_type_bills == "online" and move.move_type == "in_invoice":
                _logger.info(f"Payment request conditions met for move: {move.name}")
                if move.employee_id == False:
                    raise UserError(_("You must select an employee to process the payment"))
                else:
                    _logger.info(f"Calling request_payment for move: {move.name}")
                    move.request_payment()
            else:
                _logger.info(f"Payment request conditions NOT met for move: {move.name}")

    def unapprove_bills_all(self):
        move_ids = self.mapped('id')
        self.env['account.move'].browse(move_ids).write({'approved': False})

    def open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def create_check_button(self):
        
        self.ensure_one()
        wizard_view = self.env.ref('account.view_account_payment_register_form')
        context = {
            'active_model': 'account.move',
            'default_communication': self.reference,
        }
        
        # Add logic to choose a journal with check option
        # journal = self.env['account.journal'].search([('type', '=', 'bank')])
        
        # Add logic to automatically select 'Checks' in payment_method_line_id if journal
        
        return {
            'name': 'Create Check Wizard',
            'view_mode': 'form',
            'res_model': 'account.payment.register',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': wizard_view.id,
            'context': context
            }
 
        # return {
        #     'view_mode': 'form',
        #     'res_model': 'account.payment.register',
        #     'type': 'ir.actions.act_window',
        #     'target': 'new',
        #     'view_id': wizard_view.id,
        #     'context': {
        #         # 'default_amount': self.amount_due,
        #         # 'default_receiver': self.company,
        #         # 'default_date': fields.Datetime.now(),
        #         # 'default_memo': self.payment_reference,
        #         # 'default_check_number': int(partner.last_check_number) + 1 if partner.last_check_number else 1,
        #         # 'default_bank_name': partner.bank_name,
        #         # 'default_bank_address': partner.bank_address,
        #         # 'default_bank_2address': partner.bank_2address,
        #         # 'default_bank_account_number': partner.bank_account_number,
        #         # 'default_bank_routing_number': partner.bank_routing_number,
        #         # 'default_partner_id': partner.id,
        #         # 'default_authorized_signature': partner.authorized_signature,
        #     },
        # }
        # active_model
        # receiver must be partner
        #memo : bll reference
# Journal buscar cuenta de banco que sea para checks

    @property
    def _table_query(self):
        user_ids = self.env.context.get('default_user_ids', [])
        if len(user_ids) == 1:
            user_ids_tuple = f"({user_ids[0]})"
        else:
            user_ids_tuple = tuple(user_ids) if user_ids else (None,)
        return f"""
                WITH ProductInvoices AS (
                    SELECT
                        am.id AS move_id,
                        STRING_AGG(COALESCE(pt.name->>'en_US', pt.name::text), ',') AS product_inv
                    FROM account_move am
                    JOIN account_move_line aml ON am.id = aml.move_id
                    JOIN product_product pp ON aml.product_id = pp.id
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    GROUP BY am.id
                )
                SELECT
                    am.id AS id,
                    am.invoice_date AS invoice_date,
                    am.date AS date,
                    am.linked_activities AS linked_activities,
                    am.priority AS priority,
                    am.payment_reference AS payment_reference,
                    am.ref AS reference,
                    am.comments AS comments,
                    am.invoice_date_due AS invoice_date_due,
                    CASE
                        WHEN am.payment_state = 'not_paid' THEN 'Not Paid'
                        WHEN am.payment_state = 'partial' THEN 'Partially Paid'
                        WHEN am.payment_state = 'in_payment' THEN 'In Payment'
                        WHEN am.payment_state = 'paid' THEN 'Paid'
                        WHEN am.payment_state = 'reversed' THEN 'Reversed'
                        WHEN am.payment_state = 'invoicing_legacy' THEN 'Invoicing App Legacy'
                        ELSE 'Unknown'
                    END AS payment_state,
                    rp.name AS partner,
                    rc.name AS company,
                    ru.id AS user_id,
                    bool_or(pp.on_hold) as on_hold,
                    am.analytic_accounts AS property_address,
                    pi.product_inv AS product,
                    am.approved AS approved,
                    -am.amount_total_signed AS amount_total,
                    -am.amount_residual AS amount_due,
                    am.payment_type_bills AS payment_type_bills,
                    max(pc.name) AS county_name,
                    sum(budget_model.amount) AS price_estimate,
                    am.amount_total - (sum(budget_model.amount)) AS price_difference,
                    am.activity_completed AS activity_completed
                FROM account_move am
                LEFT JOIN account_move_line ON am.id = account_move_line.move_id
                LEFT JOIN account_analytic_line ON account_move_line.id = account_analytic_line.move_line_id
                LEFT JOIN pms_property pp ON account_analytic_line.account_id = pp.analytical_account
                LEFT JOIN pms_county pc ON pp.county = pc.id
                LEFT JOIN product_product ON account_move_line.product_id = product_product.id
                LEFT JOIN product_template ON product_product.product_tmpl_id = product_template.id
                LEFT JOIN budget_model ON am.partner_id = budget_model.supplier 
                    AND account_move_line.activity = budget_model.activity
                    AND pp.city = budget_model.city 
                    AND pp.house_model = budget_model.house_model 
                    AND product_template.id = budget_model.product_model 
                LEFT JOIN res_partner rp ON am.partner_id = rp.id
                LEFT JOIN res_company rc ON am.company_id = rc.id
                LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
                LEFT JOIN res_partner rp2 ON ru.partner_id = rp2.id
                LEFT JOIN ProductInvoices pi ON am.id = pi.move_id
                WHERE am.payment_state IN ('not_paid', 'partial')
                    AND am.state NOT IN ('draft', 'cancel')
                    AND am.move_type = 'in_invoice'
                    AND ru.id IN {user_ids_tuple}
                GROUP BY
                    am.id, 
                    pi.product_inv,
                    am.invoice_date,
                    am.date,
                    am.payment_reference,
                    am.ref, 
                    rp.name, 
                    rc.name,
                    ru.id, 
                    am.analytic_accounts, 
                    am.activity_completed, 
                    am.approved, 
                    am.amount_total, 
                    am.payment_type_bills,
                    am.payment_state
        """
        # self._cr.execute("""
        #     CREATE OR REPLACE FUNCTION update_approve_bills() RETURNS TRIGGER AS $$
        #     BEGIN
        #         UPDATE account_move SET approved = NEW.approved WHERE id = NEW.id;
        #         RETURN NEW;
        #     END;
        #     $$ LANGUAGE plpgsql;
        # """)
        # self._cr.execute("""
        #     CREATE TRIGGER trg_update_approve_bills
        #     INSTEAD OF UPDATE ON approve_bills
        #     FOR EACH ROW
        #     EXECUTE FUNCTION update_approve_bills();
        # """)

class add_approve_bills_comments(models.TransientModel):
    _name = "add.approve.bills.comments"
    _description = "Update Approve Bills Comments"
    
    comments = fields.Char(string="Comments")


    def add_approve_bills_comments(self): # UPDATE OWNER CALL DAY FUNCTION
        count = 0
        bills = self.env.context.get('active_ids')
        if not bills:
            return self.env['update.owner.call.day'].simple_notification("error", "Error", "Unable to find any records to update.", False)
        
        for bill in bills:
            selected_bill = self.env['account.move'].search([('id', '=', bill)])
            if not selected_bill: continue
            
            selected_bill.update({'comments': self.comments})
            count += 1

        if count > 1: message = ("%s comments added." % count)
        else: message = "Comment added."
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': message, 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
        }
    

class update_bill_priority_wizard(models.TransientModel):
    _name = "update.bill.priority.wizard"
    _description = "Update Bill Priority Wizard"
    
    priority = fields.Selection([('0', 'None'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')

    def update_priority(self):
        bills = self.env.context.get('active_ids')
        count = 0
        if not bills:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "Unable to find any records to update.",
                    'type': 'info',
                    'sticky': False,
                }
            }

        bills_to_update = self.env['account.move'].browse(bills)
        bills_updated = bills_to_update.write({'priority': self.priority})
        count = len(bills_to_update) if bills_updated else 0

        if count > 1:
            message = ("%s bills updated with priority: %s" % (count, dict(self._fields['priority'].selection).get(self.priority)))
        elif count == 1:
            message = ("1 bill updated with priority: %s" % dict(self._fields['priority'].selection).get(self.priority))
        else:
            message = "No bills were updated."

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
        
        
class UpdateBillUserWizard(models.TransientModel):
    _name = 'update.bill.user.wizard'
    _description = 'Update Bill User Wizard'

    user_id = fields.Many2one("res.users", string="User", required=True)

    def update_user(self):
        """
        Action to update the user field on the selected bill records.
        """
        active_ids = self.env.context.get('active_ids', [])
        
        # Browse the records from the approve.bills model first, as that's what's
        # selected in the report's tree view.
        report_bills = self.env['approve.bills'].browse(active_ids)
        
        # The 'id' field in the report model is actually the ID of the account.move record.
        # We need to map these IDs to get a list of the underlying bill IDs.
        bill_ids_to_update = report_bills.mapped('id')
        
        bills_to_update = self.env['account.move'].browse(bill_ids_to_update)
        
        updated_count = 0
        
        if bills_to_update:
            # Note: The 'invoice_user_id' field is the standard field for the responsible user.
            bills_to_update.sudo().write({'invoice_user_id': self.user_id.id})
            updated_count = len(bills_to_update)

        if updated_count > 0:
            message = f"{updated_count} bills updated with user: {self.user_id.name}"
        else:
            message = "No bills were updated."
        
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