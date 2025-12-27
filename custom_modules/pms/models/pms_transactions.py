from odoo import api, models, fields
from odoo.fields import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from collections import defaultdict


class pms_transactions(models.Model):
    _name = "pms.transactions"
    _description = "Transactions History"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Transaction Name", compute="_transaction_full_name", store=True)
    property_address = fields.Many2one("pms.property", string="Property Address")
    transaction_date = fields.Date(string="Transaction Date")
    transaction_type = fields.Selection([
            ('sale', "Sale"),
            ('purchase', "Purchase"),
            ('refinance', "Refinance")
        ], string="Type", tracking=True)
    lender = fields.Many2one("res.partner", string="Borrower")
    owner = fields.Many2one("res.partner", string="New Owner")
    old_owner = fields.Many2one("res.partner", string="Old Owner")
    active = fields.Boolean(string="Active", default=True)

     # === Currency fields === #
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True
    )

    transaction_id = fields.Many2one("account.move", string="Accounting Journal", readonly=True)
    asset_product = fields.Many2one("product.product", string="Asset Product")
    is_rent = fields.Boolean(string="Is it going to be rented")
    is_construction = fields.Boolean(string="Is it going to be for construction")
    is_thirdpart = fields.Boolean(string="Is it going to be for thirdparty construction")
    status = fields.Selection(selection=[("draft", "Draft"), ("posted", "Posted")], default="draft")
    attachment = fields.Many2many('ir.attachment', string="Attachments")
    analytical_account = fields.Many2one(related="property_address.analytical_account", string="Analytical Account")
    parcel_id = fields.Char(related="property_address.parcel_id", string="Parcel ID")
    invested_external_money = fields.Boolean(string="Invested External Money", default=False)

    def open_transactions_journal_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transaction Journal Wizard',
            'res_model': 'pms.transaction.journal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_transaction_id': self.id,
                        'default_transaction_type': self.transaction_type,
                        'default_owner': self.owner.id,
                        'default_old_owner': self.old_owner.id,
                        'default_property_address': self.property_address.id,
                        'default_residential_unit_closure': self.property_address.residential_unit_closure}
        }
        
    
    @api.depends("transaction_date","transaction_type","owner","old_owner")
    def _transaction_full_name(self):
        if self.name:
            pass
        else:
            for record in self:
                if record.transaction_date and record.transaction_type and record.owner and record.old_owner:
                    record.name = f"{record.transaction_date} {record.transaction_type}, {record.owner.name} {record.old_owner.name}"
                else:
                    record.name = " "
    
    def _get_total_balance(self, property_id):
        company_idd = self.env["res.company"].sudo().search([("partner_id", "=", self.old_owner.id)]).id
        analytic_line_obj = self.env['account.analytic.line'].sudo().search(["&", ("account_id", "=", property_id.analytical_account.id), ("company_id", "=", company_idd)])
        balance = -sum(analytic_line_obj.sudo().mapped("amount"))
        return balance         


    def post_journal_entry(self):
        for record in self:
            
            properties = record.env["pms.property"].sudo().search([("id", "=", record.property_address.id)])
            properties.partner_id = record.owner
            record.status = "posted"

            if record.analytical_account:
                    change_analytical = record.env["account.analytic.account"].search([("id", "=", record.analytical_account.id)])
                    change_analytical.sudo().write({"name": record.property_address.name + " " + record.parcel_id + " " + record.owner.name,
                                                    "partner_id": record.owner.id})
            
            if properties.mapped('analytical_account'):
                pass

            else:
                properties._property_analytical()

            
            if record.transaction_type == "refinance":
            #record._create_refinance_entry()
                properties.own_third = "own"
                loans_to = record.env["pms.loans"].search(["&", ("exit_status", "=", "ongoing"),("property_address.id", "=", record.property_address.id)])
                loans_to.exit_status = "refinanced"
                
                if record.is_rent:
                    properties.available_for_rent = True

                if record.is_construction:
                    properties.status_property = "construction"

                elif record.is_thirdpart:
                    properties.own_third = "third"
                    properties.status_property = "construction"

                return {
                'type': 'ir.actions.act_window',
                'res_model': 'pms.loans',
                'view_mode': 'form'}

            
            elif record.transaction_type == "purchase":
            #record._create_purchase_entry()
                properties.own_third = "own"
                if record.is_construction:
                    properties.status_property = "construction"

                if record.is_rent:
                    properties.available_for_rent = True

                elif record.is_thirdpart:
                    properties.own_third = "third"
                    properties.status_property = "construction"


            elif record.transaction_type == "sale":
                #record._create_sold_entry()
                properties.own_third = "third"
                properties.status_property = "sold"

                if record.is_thirdpart:
                    properties.own_third = "third"
                    properties.status_property = "construction"



    def _create_refinance_entry(self):
        if self.is_rent:
            lines_property = []
            for x in self.property_address:
                dic = {}
                balance = self._get_total_balance(x)
                dic["amount"] = balance
                dic["account"] = x.analytical_account.id

                lines_property.append(dic)
                x.status_property = "rented"
                x.partner_id = self.owner.id
            
            header = self._prepare_header_entry()
            lines = []
            for x in lines_property:
                line = self._prepare_line_entry(x)
                lines.append(Command.create(line))
            
            header['invoice_line_ids'] += lines 

            invoice = self.env["account.move"].sudo().create(header)

            self.transaction_id = invoice.id

            return {
            'type': 'ir.actions.act_window',
            'name': ('view_move_tree'),
            'context': "{'move_type':'out_invoice'}",
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id}

            

        elif self.is_construction:
            pass
    
    def _prepare_header_entry(self):
        company_idd = self.env["res.company"].sudo().search([("partner_id", "=", self.old_owner.id)]).id
        header = {
            "move_type": "in_invoice",
            "ref": self.name,
            "date": self.transaction_date,
            "invoice_date": self.transaction_date,
            'invoice_line_ids': [],
            "partner_id": self.owner.id,
            "company_id": company_idd
        }
        
        return header
    
    def _prepare_line_entry(self, x):
        lines = {
            "product_id": self.asset_product.id,
            "quantity": 1,
            "price_unit": x["amount"],
            "analytic_distribution": {str(x["account"]): 100.0}
        }

        return lines
    
    def _create_purchase_entry(self):
        if self.is_rent:
            pass

        elif self.is_construction:
            pass
    

    def _create_sold_entry(self):
        if self.is_thirdpart:
            pass

        else:
            pass



