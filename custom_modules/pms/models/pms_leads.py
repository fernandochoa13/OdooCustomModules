from odoo import api, models, fields
from odoo.fields import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from collections import defaultdict


class pms_leads(models.Model):
    _name = "pms.leads"
    _description = "Transaction Leads"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Lead Name", compute="_lead_full_name", store=True)
    property_address = fields.Many2one("pms.property", string="Property Address", required=True)
    lead_type = fields.Selection([
            ('sale', "Sale"),
            ('purchase', "Purchase"),
            ('refinanced', "Refinanced"),
        ], string="Lead Type", tracking=True)
    client = fields.Many2one("res.partner", string="Client")
    salesperson = fields.Many2one("res.partner", string="Salesperson")
    comments = fields.Text(string="Comments")
    lead_state = fields.Selection(
        [('lead', "Lead"),('converted', "Converted")], 
        string="Lead State", tracking=True, default="lead")
    county = fields.Many2one(related="property_address.county", string="County", required=True)
    lot_parcel_id = fields.Char(string="Lot Parcel ID")
    sent_survey = fields.Selection([
            ('yes', "Yes"),
            ('no', "No"),
            ('hold', "Hold"),
            ('cancellation_sent', "Cancellation Sent"),
        ], string="Sent for Survey", tracking=True)
    lot_inspection = fields.Selection([
            ('approved', "Approved"),
            ('denied', "Denied"),
            ('hold', "Hold"),
            ('sent_inspection',  "Sent for Inspection"),
        ], string="Lot Inspection", tracking=True)
    escrow_request = fields.Float(string="Escrow Requests")
    escrow_status = fields.Selection([
            ('sent', "Sent"),
            ('not_sent', "Not Sent")
        ], string="Escrow Status", tracking=True)
    initial_proposal = fields.Float(string="Initial Proposal")
    business_decision = fields.Selection(
        [('build', "Build"),('wholesale', "Wholesale"), ('hold', "Hold"),('canceled', "Canceled"),('pending', "Pending")], 
        string="Business Decision", tracking=True, default="")
    loan = fields.Many2one("pms.loans", string="Loan")
    week_number = fields.Char(string="Week Number")
    closing_date = fields.Date(string="Closing Date")
    acquisition_status = fields.Selection([
            ('pending', "Pending"),
            ('closed', "Closed"),
            ('probate', "Probate")
        ], string="Acquisition Status", tracking=True)
    file_opened = fields.Selection([
            ('not_sent', "Not Sent"),
            ('closed', "Closed"),
            ('opened', "Opened")
        ], string="File Open", tracking=True)
    turtle_tree_inspection = fields.Char(string="Turtle Tree Inspection")
    scrub_jays = fields.Boolean(string="Scrub Jays")
    hoa = fields.Char(string="HOA")
    inspection_due_date = fields.Date(required=True, string="Inspection Due Date")
    attachment_ids = fields.Many2many('ir.attachment', compute='_compute_attachments')
    

    @api.depends("lead_type","client","salesperson")
    def _lead_full_name(self):
        for record in self:
            if record.lead_type and record.client and record.salesperson:
                record.name = f"{record.lead_type}, {record.client.name} from {record.salesperson.name}"
            else:
                record.name = " "

    def _compute_attachments(self):
        attachment_ids = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id)
            ])
        self.attachment_ids = attachment_ids.ids

    @api.depends("lead_type","client","salesperson","property_address")
    def convert_lead_to_transaction(self):
        dup_check = self.env["pms.transactions"].search(["&",("name", "=", self.name), "&",("transaction_type", "=", self.lead_type), "&",("owner", "=", self.client.id), ("old_owner", "=", self.salesperson.id)])
        if dup_check:
            raise UserError("This lead has already been converted to a transaction")
        else:
            self.lead_state = "converted"
            draft_transaction = {
                "name": self.name,
                "property_address": self.property_address.id,
                "transaction_type": self.lead_type,
                "owner": self.client.id,
                "old_owner": self.salesperson.id,
                "status": "draft",
                "attachment": [(6, 0, self.attachment_ids.ids)]
            }
            self.env["pms.transactions"].create(draft_transaction)

    def back_to_lead(self):
        self.lead_state = "lead"
