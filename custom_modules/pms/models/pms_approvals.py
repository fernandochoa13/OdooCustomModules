from odoo import models, fields, api

class ApprovalRequest(models.Model):
    _name = 'pms.approval'
    _description = 'Approval Request'

    name = fields.Char(string='Name', required=True, readonly=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, readonly=True)
    final_date = fields.Date(string='Final Date', required=True, readonly=False)
    description = fields.Text(string='Description', readonly=True)
    status = fields.Selection([
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('denied', 'Denied')
    ], string='Status', default='to_approve', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True)
    source = fields.Selection([
        ('job_completion', 'Job Completion'),
        ('dispute', 'Dispute')
    ], string='Source', readonly=True)

    activity_id = fields.Many2one('pms.projects.routes', string='Activity', readonly=True)

    def action_approve(self):
        for record in self:
            record.status = 'approved'
            if record.source == 'job_completion':
                record.activity_id._complete_jobs(record.final_date)
            elif record.source == 'dispute':
                record.activity_id.disputed = True
                record.activity_id.to_approve_dispute = False

    def action_deny(self):
        for record in self:
            record.status = 'denied'
            if record.source == 'job_completion':
                record.activity_id.to_approve = False
            #notify the employee that the request was denied
            elif record.source == 'dispute':
                record.activity_id.to_approve_dispute = False
            
            
                
