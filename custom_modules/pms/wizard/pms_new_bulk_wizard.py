from odoo import models, fields, api

class pms_new_bulk_wizard(models.TransientModel):
    _name = 'new.bulk.wizard'
    _description = 'New Bulk Wizard'

    projects = fields.Many2many("pms.projects", string='Projects')
    vendor = fields.Many2one("res.partner", string="Vendor")
    act_name = fields.Many2one("pms.projects.routes.templates.lines", string="Activity")
    
    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
    def create_activities(self):
        for record in self:
            for project in record.projects:
                activities = {
                    "name": record.act_name.id,
                    "vendor": record.vendor.id,
                    "project_property": project.id,
                }
                record.env["pms.projects.routes"].create(activities)
        return {'type': 'ir.actions.act_window_close'}