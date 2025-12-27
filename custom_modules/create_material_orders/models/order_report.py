from odoo import  fields, models, _
from odoo.exceptions import ValidationError



class verify_order_report_wizard(models.TransientModel):
    _name = 'verify.order.report.wizard'
    _description = 'Verify Order Report Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)

    def open_orders_wizard(self):
        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])
        tree_view = self.env.ref('pms.pms_materials_view_status_tree')
        form_view = self.env.ref('pms.pms_materials_view_status_form')
        search_view = self.env.ref('pms.pms_materials_view_status_search')
        if pin_verification:
            return {
                'name': 'PMS Materials',
                'type': 'ir.actions.act_window',
                'res_model': 'pms.materials',
                'view_mode': 'tree,form',
                'view_id': tree_view.id,
                'views': [(tree_view.id, 'tree'), (form_view.id, 'form'), (search_view.id, 'search')],
                'target': 'current',
                'context': {'search_default_ordercreator': 1, 'order_creator': self.employee_id.id},
            }   
        else:
            raise ValidationError(_('Invalid Employee PIN'))