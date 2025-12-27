from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from datetime import date


class verification_wizard(models.TransientModel):
    _name = 'verification.wizard'
    _description = 'Verification Wizard'

    # Verification
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)
    
    def verify_employee_wizard(self):
        
        employee = self.env['hr.employee'].search([
            ('id', '=', self.employee_id.id),
            ('pin', '=', self.employee_pin)
        ], limit=1)
        
        if employee:
            return employee
        else:
            raise ValidationError(_('Invalid Employee PIN'))

    