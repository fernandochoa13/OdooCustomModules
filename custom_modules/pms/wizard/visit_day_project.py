from odoo import models, fields, api
from odoo.exceptions import UserError

class VisitDayProject(models.TransientModel):
    _name = 'visit.day.project.wizard'
    _description = 'Visit Days in Bulk Wizard'

    type_visit_day = fields.Selection([
        ('first_visit', 'First Visit Day'),
        ('second_visit', 'Second Visit Days'),
        ('both_days', 'Both'),
    ], string="Type of Visit Day", default="")
    day_of_week = fields.Selection(selection=[("monday", "Monday"),("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday")], string="1st Day of the week") # Unknown parameter: tracking=True
    day_of_week_second = fields.Selection(selection=[("monday", "Monday"),("tuesday", "Tuesday"), ("wednesday", "Wednesday"), ("thursday", "Thursday"), ("friday", "Friday"), ("saturday", "Saturday")], string="2nd Day of the week") # Unknown parameter: tracking=True

    
    def set_visit_days(self):
        res_ids = self.env.context.get('active_ids')
        records = self.env["pms.projects"].search([('id', '=', res_ids)])
        for record in records:
            if self.type_visit_day == "first_visit":
                record.sudo().write({'visit_day': self.day_of_week})
            elif self.type_visit_day == "second_visit":
                record.sudo().write({'second_visit_day': self.day_of_week})
            elif self.type_visit_day == "both_days":
                record.sudo().write({
                    'visit_day': self.day_of_week,
                    'second_visit_day': self.day_of_week_second,
                    })
            else:
                raise UserError("Invalid visit day type")
        return {'type': 'ir.actions.act_window_close'}