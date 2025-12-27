from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
from odoo.fields import Command
from datetime import date
import base64
import io
from odoo.tools import SQL


class pms_draws(models.Model):
    _name = "pms.draws"
    _description = "Table for loans draws"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    display_name = fields.Char(string="Name", compute="_compute_name", store=True)
    name = fields.Char(string="Ref")
    loan_id = fields.Many2one("pms.loans", string="Loan id")
    loan_type_draw = fields.Selection(related="loan_id.loan_type", string="Loan Type", readonly=True)
    loan_lender = fields.Many2one(related="loan_id.lender", string="Lender", readonly=True)
    loan_amount = fields.Monetary(related="loan_id.loan_amount", string="Loan Amount", currency_field='company_currency_id', readonly=True)
    available_loan_balance = fields.Monetary(related="loan_id.available_balance", string="Available Loan Balance", currency_field='company_currency_id', readonly=True)
    address = fields.Many2one(related="loan_id.property_address", readonly=True)
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
        ], compute="_compute_project_phase", string="Project Phase", readonly=True)
    county = fields.Many2one(related="address.county", readonly=True)
    draw_amount = fields.Monetary(string="Draw Amount", currency_field='company_currency_id', compute="_calculate_draw_amount", readonly=True)
    draw_fee = fields.Monetary(string="Draw Fee", currency_field='company_currency_id')
    memo = fields.Char(string="Memo")
    date = fields.Date(string="Draw Date")
    status = fields.Selection(selection=[("draft","Draft"), ("posted", "Posted"), ("pending", "Pending")], default="draft")
    draw_lines = fields.One2many("pms.draw.lines", "draw_id", string="Draw Lines")

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

    @api.depends("address")
    def _compute_project_phase(self):
        for record in self:
            projects = record.env["pms.projects"].search([("address", "=", record.address.id)]).ids
            if projects:
                project = record.env["pms.projects"].browse(projects[0])
                record.project_phase = project.status_construction
            else:
                record.project_phase = "pending"

    @api.depends("address", "date", "name")
    def _compute_name(self):    
        for record in self:
            if record.address and record.date and record.name:
                record.display_name = f'{record.address.name} - {record.name} - {record.date}'

    def print_draws_report(self):
        return self.env.ref('pms.report_draws_pms_action').report_action(self)

    def too_post(self):
        self.status = "posted"

    def too_draft(self):
        self.status = "draft"

    def to_pending(self):      
        self.status = "pending"

    def _calculate_draw_amount(self):
        for record in self:
            draw_line = record.env["pms.draw.lines"].sudo().search([("draw_id", "=", record.id)])
            draw_lines = sum(draw_line.sudo().mapped("amount_drawed"))
            record.draw_amount = draw_lines

    def _send_daily_report_draws(self):

        end_of_day = datetime.combine(datetime.now(), time.max ) - timedelta(days=1)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=1)

        records = self.search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])

        data_record = base64.b64encode(self.env.ref("pms.report_draws_pms_action").sudo()._render_qweb_pdf(self.env.ref("pms.report_draws_pms_action").ids[0], records.ids)[0])        
        ir_values = {
                'name': "DailyDrawsReport%s.pdf" % date.today(),
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record
                }
        data_id = self.env['ir.attachment'].create(ir_values)
                
        email_template = self.env.ref('pms.email_template_draws_report_daily')
        i = 0
        for record in self:
                if i < 1:
                    email_template.attachment_ids = [(4, data_id.id)]
                    email_template.send_mail(record.id, force_send=True)
                    email_template.attachment_ids = [(5, 0, 0)]

                    i = i + 1
        else:
            pass

    def _send_weekly_report_draws(self):

        end_of_day = datetime.combine(datetime.now(), time.max)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=7)

        records = self.search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])

        data_record = base64.b64encode(self.env.ref("pms.report_draws_pms_action").sudo()._render_qweb_pdf(self.env.ref("pms.report_draws_pms_action").ids[0], records.ids)[0])        
        ir_values = {
                'name': "WeeklyDrawsReport%s.pdf" % date.today(),
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record
                }
        data_id = self.env['ir.attachment'].create(ir_values)
            
        email_template = self.env.ref('pms.email_template_draws_report')
        i = 0
        for record in self:
                if i < 1:
                    email_template.attachment_ids = [(4, data_id.id)]
                    email_template.send_mail(record.id, force_send=True)
                    email_template.attachment_ids = [(5, 0, 0)]

                    i = i + 1
        else:
            pass

    
    