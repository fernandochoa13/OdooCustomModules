from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from datetime import date


class verify_orders_wizard(models.TransientModel):
    _name = 'verify.orders.wizard'
    _description = 'Verify Orders Wizard'

    # Verification
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_pin = fields.Char(string='Employee PIN', required=True)
    
    def create_order_wizard(self):

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])
        form_view = self.env.ref('create_material_orders.create_order_wizard_form')
        
        if pin_verification:
            return {
                'name': 'New Material Order',
                'type': 'ir.actions.act_window',
                'res_model': 'create.order.wizard',
                'view_mode': 'form',
                'view_id': form_view.id,
                'target': 'fullscreen',
                'context': {'default_order_creator': self.employee_id.id}
                
            }
        else:
            raise ValidationError(_('Invalid Employee PIN'))

    def open_orders_wizard(self):

        pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])
        redirect = {
                'name': 'Material Orders',
                'type': 'ir.actions.act_window',
                'res_model': 'pms.materials',
                'views': [
                    [self.env.ref('create_material_orders.material_orders_view_kanban').id, 'kanban'],
                    [self.env.ref('create_material_orders.material_orders_view_tree').id, 'tree'], 
                    [self.env.ref('create_material_orders.material_orders_view_calendar').id, 'calendar'], 
                ],
                'target': 'fullscreen',
                # 'domain': [('order_creator', '=', self.employee_id.id)],
                'context': {
                    'default_order_creator': self.employee_id.id,
                    # 'search_default_waiting_conf': 1
                    }
            }
        
        if pin_verification:
            return redirect
        else:
            raise ValidationError(_('Invalid Employee PIN'))
        #employee_id = self._context.get('default_employee')
        

        

class confirm_orders_wizard(models.TransientModel):
    _name = 'confirm.orders.wizard'
    _description = 'Confirm Orders Wizard'

    #employee_id = self._context.get('default_employee')
    confirmed_by = fields.Many2one('hr.employee', string='Confirmed By', readonly=True)
    signature = fields.Binary(string='Signature')
    order_lines = fields.Text(string="Order Lines", readonly=True)
    quant_qual = fields.Boolean(string='I confirm that the order quality and quantities are correct', required=True)

    @api.model
    def default_get(self, fields):
        res = super(confirm_orders_wizard, self).default_get(fields)

        employee_id = self.env.context.get('default_employee')
        
        if employee_id:
            res.update({
                'confirmed_by': employee_id
            })
        
        material_line_ids = self.env.context.get('material_lines', [])
        
        if isinstance(material_line_ids, list):
            order_lines_data = []
            material_lines = self.env['pms.materials.lines'].browse(material_line_ids)
            
            for line in material_lines:
                formatted_line = (
                    f"Product: {line.product.name or ''} - "
                    f"Subproduct: {line.subproduct.name or ''} - "
                    f"Quantity: {line.quantity} - "
                    f"Unit Measure: {line.unit_measure or ''} - "
                    f"Amount: {line.amount} - "
                    f"Total: {line.total}"
                )
                order_lines_data.append(formatted_line)
            
            res.update({
                'order_lines': "\n".join(order_lines_data), 
            })
        
        return res


    def confirm_order(self):
        order_id = self._context.get('order_id')
        order = self.env['pms.materials'].browse(order_id)
        order.sudo().write({
            'order_status': 'delivered',
            'signed_by': self.signature,
            'confirmed_by': self.confirmed_by.id,
            'actual_delivery_date': fields.Datetime.now(),
            'ordered_to_delivered': (date.today() - order.ordered_date.date()).days if order.ordered_date else None
        })

        action = {
            'name': 'PMS Materials',
            'type': 'ir.actions.act_window',
            'res_model': 'pms.materials',
            'res_id': order_id,
            'view_mode': 'form',
            'target': 'current',
        }
    
        return action

    def reject_order(self):
        employee_id = self._context.get('default_employee')
        order_id = self._context.get('order_id')
        return {
                'name': 'Reject Orders Wizard',
                'type': 'ir.actions.act_window',
                'res_model': 'reject.orders.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'order_id': order_id,
                            'default_rejected_by': employee_id}
            }


class reject_orders_wizard(models.TransientModel):
    _name = 'reject.orders.wizard'
    _description = 'Reject Orders Wizard'

    rejected_by = fields.Many2one('hr.employee', string='Rejected By') 
    rejection_note = fields.Text(string='Rejection Note')
    signed_by = fields.Binary(string='Signature')
    attachments = fields.Many2many('ir.attachment', string='Attachments')

    def reject_order(self):
        order_id = self._context.get('order_id')
        order = self.env['pms.materials'].browse(order_id)
        order.sudo().write({
            'order_status': 'rejected',
            'rejection_note': self.rejection_note,
            'rejections_count': order.rejections_count + 1,
            'signed_by': self.signed_by,
            'rejected_date': fields.Datetime.now()
        })
        order.delivered_to_ordered_calculator()

        for attachment in self.attachments:
            attachment.copy({'res_model': 'pms.materials', 'res_id': order_id})

        action = {
            'name': 'PMS Materials',
            'type': 'ir.actions.act_window',
            'res_model': 'pms.materials',
            'res_id': order_id,
            'view_mode': 'form',
            'target': 'current',
        }
    
        return action