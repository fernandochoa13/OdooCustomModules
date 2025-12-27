from odoo import models, fields, api
from odoo.exceptions import UserError

class AskApproveWizard(models.TransientModel):
    _name = 'pms.askapprove'
    _description = 'Ask Approve Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    pin = fields.Char(string='PIN')

    def create_approval_record(self):
        if self.employee_id.pin == self.pin:
            jobs = self.env.context.get('jobs')
            for job in jobs:
                approval_vals = {
                    'employee_id': self.employee_id.id,
                    'source': 'job_completion',
                    'description': job['description'],
                    'activity_id': job['activity_id'],
                    'name': job['name'],
                    'final_date': job['final_date']
                    # Add other fields for the approval record
                }
                self.env['pms.approval'].sudo().create(approval_vals)
        else:
            # Handle incorrect PIN scenario
            raise UserError('Incorrect PIN')
