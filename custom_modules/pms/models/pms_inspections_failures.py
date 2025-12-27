from odoo import models, fields, api

class pms_inspections_failures(models.Model):
    _name = 'pms.inspections.failures'
    _description = 'PMS Inspections Failures'

    failure_number = fields.Integer(string='Failure Number', required=True, readonly=True)
    fail_reason = fields.Text(string='Failure Reason', required=True, readonly=True)
    fail_date = fields.Date(string='Failure Date', required=True, readonly=True)
    inspection_id = fields.Many2one('pms.inspections', string='Inspection', required=True, readonly=True)