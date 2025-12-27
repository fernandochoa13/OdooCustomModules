from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    allowed_to_give_points = fields.Many2many(
        'hr.employee',
        'employee_allowed_to_give_points_rel',  # This is the relation table name
        'employee_id',                  # This is the current model field
        'allowed_to_give_points_id',            # This is the related model field
        string='Allowed to give points to'
    )

    
    # allowed_to_give_points = fields.One2many('hr.points.allowed', 'employee_id', string='Allowed to give points to')
    # allowed_to_give_points = fields.Many2many('hr.employee', string='Allowed to give points to')
    # allowed_from_give_points = fields.Many2one('hr.points.allowed', string='Allowed from to give points')

# class HrPointsAllowed(models.Model):
#     _name = 'hr.points.allowed'
#     _description = 'Points Allowed'

#     employee_id = fields.Many2one('hr.employee', string='Employee')
#     allowed_to = fields.One2many('hr.employee', 'allowed_from_give_points', string='Employee')

class HrPoints(models.Model):
    _name = "hr.points"
    _description = "Points"

    received_by = fields.Many2one('hr.employee', string='Employee')
    points = fields.Integer(string='Points')
    date = fields.Date(string='Date')
    description = fields.Text(string='Description')
    given_by = fields.Many2one('hr.employee', string='Given by')

