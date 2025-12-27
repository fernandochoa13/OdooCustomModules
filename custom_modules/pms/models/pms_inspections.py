from odoo import api, models, fields
from odoo.tools import SQL
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
from odoo.fields import Command
from datetime import date
import base64

import logging
_logger = logging.getLogger(__name__)

class pms_inspections(models.Model):
    _name = "pms.inspections"
    _description = "Table for Inspections"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Inspection Number")
    date = fields.Datetime(string="Date Created")
    status = fields.Selection(
        selection=[
            ('ordered', "Ordered"),
            ('partial_pass', "Partial Pass"),
            ('passed', "Passed"),
            ('failed', "Failed"),
            ("passed_after", "Passed After Re-Inspection")
        ],
        string="Status",
        readonly=False, tracking=True,
        default='ordered')
    address = fields.Many2one("pms.property", required=True, string="Property Address")
    county = fields.Many2one("pms.county", string="County")
    inspections_type = fields.Many2one("pms.inspections.type", string="Inspection Type", domain="[('county', '=', county)]")
    superintendent = fields.Many2one(related='address.superintendent', string="Superintendent", store=True)
    comments = fields.Text(string="Comments")
    
    # Timeline fields
    end_date = fields.Datetime(string="Date Passed", readonly=True)
    construction_status = fields.Selection(string="Construction Status", readonly=True, selection=[
            ("pending", "Pending"), ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"),
            ("pip", "PIP"), ("pps", "PPS"), ("ppa", "PPA"), ("cop", "COP"), ("cop1", "COP1"), 
            ("cop2", "COP2"), ("cop3", "COP3"), ("cop4", "COP4"), ("cop5", "COP5"), ("coc", "COC"), ("completed", "Completed")
        ])
    
    
    # Add counter
    # Change fail reason to Text
    fail_counter = fields.Integer(string="Fail Counter", default=0, readonly=True)
    fail_reason = fields.Text(string="Fail Reason", readonly=True, default='')
    
    failures = fields.One2many("pms.inspections.failures", "inspection_id", string="Failures", readonly=True)
    
    # linked_activity = fields.Many2one("pms.projects.routes", string="Linked Activity")

    # def link_activity(self):
    #     if self.linked_activity:
    #         return{
    #             'type': 'ir.actions.act_window',
    #             'name': 'Linked Activity',
    #             'res_model': 'pms.projects.routes',
    #             'res_id': self.linked_activity.id,
    #             'view_type': 'tree',
    #             'view_mode': 'tree',
    #             'target': 'current'
    #             }
    #     else:
    #         raise ValidationError("No Activity Linked to this Inspection")

    @api.model
    def create(self, vals):
        if 'address' in vals and vals['address']:
            property_id = vals['address']
            property = self.env["pms.property"].browse(property_id)
            if property:
                _logger.info(property)
                _logger.info(property.utility_phase)
                vals['construction_status'] = property.utility_phase

        record = super(pms_inspections, self).create(vals)
        return record

        
        # record.activity_create()

    # def activity_create(self):
    #     if self.inspections_type:
    #         activity_type = self.env["pms.projects.routes.templates.lines"].search([("inspection_type", "=", self.inspections_type.id)], limit=1).id
    #         project_record = self.env["pms.projects"].search([("address", "=", self.address.id)], limit=1)
    #         existing_activity = self.env["pms.projects.routes"].search([("project_property", "=", project_record.id), ("name", "=", activity_type)], limit=1)
    #         if existing_activity:
    #             pass
    #         else:
    #             activity_record = self.env["pms.projects.routes"].create({
    #             "project_property": project_record.id,
    #             "name": activity_type,
    #             "start_date": datetime.now(),
    #             "order_date": datetime.now(),
    #         })
                # self.linked_activity = activity_record.id

    def to_partial_pass(self):
        self.status = 'partial_pass'
        
    def to_pass(self):
        if self.fail_counter > 0:
            self.status = 'passed_after'
            self.end_date = datetime.now()
        else:
            self.status = 'passed'
            self.end_date = datetime.now()
        # self.linked_activity.completed = True
        # self.linked_activity.end_date = datetime.now()


    def to_fail(self):

        return{
            'type': 'ir.actions.act_window',
            'name': 'Failed Inspection Wizard',
            'res_model': 'failed.inspect.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('pms.view_failed_inspect_wizard_form').id,
            'target': 'new',
            'context': {"insp_id": self.id}}

    # def to_repass(self):
    #     self.status = 'passed_after'
    #     self.end_date = datetime.now()
    #     # self.linked_activity.completed = True
    #     # self.linked_activity.end_date = datetime.now()
    
    def to_order(self):
        self.status = 'ordered'
        

    def print_inspections_report(self):
        return self.env.ref('pms.report_inspections_action').report_action(self)

    @api.onchange('address')
    def _onchange_state(self):
        if self.address.county:
            self.county = self.address.county


    def _send_all_weekly_reports(self, group_by, domain, template, name, forkey):

        if group_by:
            data_ids = []
            lista_group = list(set(domain.mapped(str(group_by))))
            for x in lista_group:
                if forkey:
                    county_filter = domain.filtered_domain([(group_by, "=", x.name)])
                else:
                    county_filter = domain.filtered_domain([(group_by, "=", x)])
                    
                data_record = base64.b64encode(self.env.ref(template).sudo()._render_qweb_pdf(self.env.ref(template).ids[0], county_filter.ids)[0])        
                if forkey:
                    ir_values = {
                        'name': f"{name}{x.name}{date.today()}.pdf",
                        'type': 'binary',
                        'datas': data_record,
                        'store_fname': data_record
                        }
                    data_id = self.env['ir.attachment'].create(ir_values)
                else:
                    ir_values = {
                    'name': f"{name}{x}{date.today()}.pdf",
                    'type': 'binary',
                    'datas': data_record,
                    'store_fname': data_record
                    }
                data_id = self.env['ir.attachment'].create(ir_values)
                data_ids.append(data_id)
            return data_ids
        else:
            data_record = base64.b64encode(self.env.ref(template).sudo()._render_qweb_pdf(self.env.ref(template).ids[0], domain.ids)[0])        
            ir_values = {
                'name': f"{name}{date.today()}.pdf",
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record
                }
            data_id = self.env['ir.attachment'].create(ir_values)
            return data_id
                    
                    #email_template = self.env.ref('pms.email_template_inspections_report_daily')
                    #i = 0

    def _send_weekly_report(self):
        end_of_day = datetime.combine(datetime.now(), time.max) 
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=7)

        records_inspections = self.search(["|", ("status", "=", "failed"), "&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_activities = self.env["pms.projects.routes"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_draws = self.env["pms.draws"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_purchase = self.env["pms.purchase.report"].search(["|", "&",("effective_date", "<", end_of_day), ("effective_date", ">", start_of_day), "&", ("date_approved", ">", start_of_day), ("date_approved", "<", end_of_day)])
        records_utility = self.env["pms.property"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_materials = self.env["account.move.line"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])

        lista_reports = [["county", records_inspections, "pms.report_inspections_action", "Insp.", True],
                         ["county", records_activities, "pms.report_project_activities_pms_action", "Act.", True],
                         [False, records_draws, "pms.report_draws_pms_action", "Draw", False],
                         ["county", records_purchase, "pms.report_purchase_pms_action", "Purch.", False],
                         [False, records_utility, "pms.report_utility_pms_action", "Util.", False],
                         [False, records_materials, "pms.report_materials_action", "Mater.", False]
                         ]
        lista_documents = []
        for x in lista_reports:
            document = self._send_all_weekly_reports(group_by = x[0], domain=x[1], template=x[2], name=x[3] , forkey=x[4])
            lista_documents.append(document)
        lista_documents = [item for sublist in lista_documents for item in sublist]
        email_template = self.env.ref('pms.email_template_inspections_report_weekly')
        i = 0

        for record in self:
            while i < 1:
                for y in lista_documents:
                    email_template.attachment_ids = [(4, y.id)]
                
                email_value={'subject': 'Weekly Reports'}
                
                email_template.send_mail(record.id, email_values = email_value, force_send=True)
                
                email_template.attachment_ids = [(5, 0, 0)]
                
                i = i + 1
            else:
                pass



    def _send_all_daily_reports(self, group_by, domain, template, name, forkey):

        if group_by:
            data_ids = []
            lista_group = list(set(domain.mapped(str(group_by))))
            for x in lista_group:
                if forkey:
                    county_filter = domain.filtered_domain([(group_by, "=", x.name)])
                else:
                    county_filter = domain.filtered_domain([(group_by, "=", x)])
                data_record = base64.b64encode(self.env.ref(template).sudo()._render_qweb_pdf(self.env.ref(template).ids[0], county_filter.ids)[0])        
                if forkey:
                    ir_values = {
                        'name': f"{name}{x.name}{date.today()}.pdf",
                        'type': 'binary',
                        'datas': data_record,
                        'store_fname': data_record
                        }
                    data_id = self.env['ir.attachment'].create(ir_values)
                else:
                    ir_values = {
                    'name': f"{name}{x}{date.today()}.pdf",
                    'type': 'binary',
                    'datas': data_record,
                    'store_fname': data_record
                    }
                data_id = self.env['ir.attachment'].create(ir_values)
                data_ids.append(data_id)
            return data_ids
        else:
            data_record = base64.b64encode(self.env.ref(template).sudo()._render_qweb_pdf(self.env.ref(template).ids[0], domain.ids)[0])        
            ir_values = {
                'name': f"{name}{date.today()}.pdf",
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record
                }
            data_id = self.env['ir.attachment'].create(ir_values)
            return data_id
                    
                    #email_template = self.env.ref('pms.email_template_inspections_report_daily')
                    #i = 0

    def _send_daily_report(self):
        end_of_day = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=1)

        records_inspections = self.search(["|", ("status", "=", "failed"), "&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_activities = self.env["pms.projects.routes"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_draws = self.env["pms.draws"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_purchase = self.env["account.move.line"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_utility = self.env["pms.property"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])
        records_materials = self.env["account.move.line"].search(["&", ("write_date", "<", end_of_day), ("write_date", ">", start_of_day)])

        lista_reports = [["county", records_inspections, "pms.report_inspections_action", "Insp.", True],
                         ["county", records_activities, "pms.report_project_activities_pms_action", "Act.", True],
                         [False, records_draws, "pms.report_draws_pms_action", "Draws", False],
                         [False, records_purchase, "pms.report_purchase_pms_action", "Purch.", False],
                         [False, records_utility, "pms.report_utility_pms_action", "Util.", False],
                         [False, records_materials, "pms.report_materials_action", "Mater.", False]
                         ]
        lista_documents = []
        for x in lista_reports:
            document = self._send_all_daily_reports(group_by = x[0], domain=x[1], template=x[2], name=x[3] , forkey=x[4])
            lista_documents.append(document)
        lista_documents = [item for sublist in lista_documents for item in sublist]
        email_template = self.env.ref('pms.email_template_inspections_report_daily')
        i = 0

        for record in self:
            while i < 1:
                for y in lista_documents:
                    email_template.attachment_ids = [(4, y.id)]
                
                email_value={'subject': 'Daily Reports'}
                
                email_template.send_mail(record.id, email_values = email_value, force_send=True)
                
                email_template.attachment_ids = [(5, 0, 0)]
                
                i = i + 1
            else:
                pass