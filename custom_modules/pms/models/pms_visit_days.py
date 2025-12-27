from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date


class PMSVisitDays(models.Model):
    _name = "pms.visit.days"
    _description = "Table for visit days"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    property_name = fields.Many2one("pms.property", string="Property")
    project_phase = fields.Selection(related="property_name.utility_phase", string="Project Phase", readonly=True, copy=False, index=True, tracking=True, store=True) # redundant default
    project_on_hold = fields.Boolean(related="property_name.on_hold", string="Project On Hold", readonly=True, copy=False, index=True, tracking=True, store=True) # redundant default
    property_project = fields.Many2one("pms.projects", string="Project")
    visit_date = fields.Date(string="Visit Date")
    visited_by = fields.Many2one("hr.employee", string="Visited By")

    # @api.depends("property_name")
    # def _compute_project(self):
    #     for record in self:
    #         # Find the project related to the property name
    #         project = self.env['pms.projects'].search([('address', '=', record.property_name.id), ('active', '=', True)], limit=1)
    #         # Set the project if found
    #         if project:
    #             record.property_project = project.id
    #         else:
    #             record.property_project = False

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record.update_project_fields()
        return record

    def write(self, vals):
        result = super().write(vals)
        self.update_project_fields()
        return result

    def update_project_fields(self):
        projects = self.env['pms.projects'].search([
            ('address', '=', self.property_name.id)
        ])
        for project in projects:
            project._compute_last_visit_day()
            project._compute_days_since_last_visit()


class VisitDaysWizard(models.TransientModel):
    _name = "visit.days.wizard"
    _description = "Wizard for visit days"

    visit_date = fields.Date(string="Visit Date", required=True)
    visited_by = fields.Many2one("hr.employee", string="Visited By", required=True)

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
    def create_visit_days(self):
        res_ids = self.env.context.get('active_ids')
        projects = self.env["pms.projects"].search([('id', '=', res_ids)])
        for record in self:
            for project in projects:
                visit_days = {
                    "visit_date": record.visit_date,
                    "visited_by": record.visited_by.id,
                    "property_name": project.address.id,
                }
                record.env["pms.visit.days"].create(visit_days)
        return {'type': 'ir.actions.act_window_close'}
    
class PMSPlannedVisitDays(models.Model):
    _name = "pms.planned.visit.days"
    _description = "Table for planned visit days"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    planned_property = fields.Many2one("pms.property", string="Planned Property")
    project_phase = fields.Selection(related="planned_property.utility_phase", string="Project Phase", readonly=True, copy=False, index=True, tracking=True, store=True) # redundant default
    planned_visit_date = fields.Date(string="Planned Visit Date")
    planned_visitor = fields.Many2one("hr.employee", string="Planned Visitor")

class PlannedVisitDaysWizard(models.TransientModel):
    _name = "planned.visit.days.wizard"
    _description = "Wizard for Planned visit days"

    planned_visit_date = fields.Date(string="Planned Visit Date", required=True)
    planned_visitor = fields.Many2one("hr.employee", string="Planned Visitor", required=True)

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
    def create_planned_visit_days(self):
        res_ids = self.env.context.get('active_ids')
        projects = self.env["pms.projects"].search([('id', '=', res_ids)])
        for record in self:
            for project in projects:
                visit_days = {
                    "planned_visit_date": record.planned_visit_date,
                    "planned_visitor": record.planned_visitor.id,
                    "planned_property": project.address.id,
                }
                record.env["pms.planned.visit.days"].create(visit_days)
        return {'type': 'ir.actions.act_window_close'}
