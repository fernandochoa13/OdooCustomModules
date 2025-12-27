from odoo import models, fields, api

from odoo.exceptions import UserError

class GivePointsWizard(models.TransientModel):
    _name = 'give.points.wizard'
    _description = 'Give Points Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    pin = fields.Char(string='PIN')

    def action_confirm(self):
        # Check if the PIN is correct
        if self.pin == self.employee_id.pin:  # Replace '1234' with the correct PIN
            # Redirect to another wizard
            return {
                'name': '2nd Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'give.points.2.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'employee_id': self.employee_id.id}
            }
        else:
            raise UserError('Pin is incorrect')
        
    class GivePoints2Wizard(models.TransientModel):
        _name = 'give.points.2.wizard'
        _description = 'Give Points 2 Wizard'

        original_employee_id = fields.Many2many('hr.employee', string='Employee', default=lambda self: self.env['hr.employee'].browse(self._context.get('employee_id')).allowed_to_give_points.ids) 
        date = fields.Date(string='Date', default=fields.Date.today())
        description = fields.Text(string='Description')
        points = fields.Integer(string='Points')
        employee = fields.Many2one('hr.employee', string='Employee', domain="[('id', 'in', original_employee_id)]")

        def create_hr_points_record(self):
            hr_points = self.env['hr.points'].create({
                'date': self.date,
                'description': self.description,
                'points': self.points,
                'received_by': self.employee.id,
                'given_by': self._context.get('employee_id')
            })
            return hr_points