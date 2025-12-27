from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

import re


class create_order_wizard(models.TransientModel):
    _name = 'create.order.wizard'
    _description = 'Create Order Wizard'

    id = fields.Integer('id', readonly=True)
    order_creator = fields.Many2one('hr.employee', string='Order Creator', readonly=True, default=lambda self: self.env.context.get('default_order_creator'))
    property_id = fields.Many2one('pms.property', string='Property', required=False)
    order_date = fields.Datetime('Order Date', required=True, default=lambda self: self.get_current_date())
    house_model = fields.Many2one('pms.housemodels', string='House Model', required=False)
    county = fields.Many2one('pms.county', string='House County', required=False)
    purchase_template = fields.Many2one("purchase.template", string="Purchase Template")
    ask_for_measure = fields.Boolean(related="purchase_template.ask_for_measurement", string="Ask for Measure") # redundant default
    comments = fields.Text('Comments')
    special_order = fields.Boolean('Special Order')
    order_wizard_lines = fields.One2many('create.order.wizard.line', 'wizard_id', string='Order Wizard Lines')
    order_wizard_lines_ro = fields.One2many('create.order.wizard.line.ro', 'wizard_id_ro', string='Order Wizard Lines Ro')

    def get_current_date(self):
        return fields.datetime.now()
    

    @api.onchange('purchase_template')
    def _onchange_purchase_template(self):
        self.order_wizard_lines.unlink()
        lines = []
        for line in self.purchase_template.template_lines:
            lines.append((0, 0, {
                'product': line.product.id,
                'subproduct': line.subproduct.id,
                'quantity': line.quantity,
                'unit_measure': line.unit_measure,
                'amount': line.amount,
                'total': line.total,
            }))
        self.order_wizard_lines = lines
        self.order_wizard_lines_ro = lines

    @api.onchange('property_id')
    def property_selected(self):
        if self.property_id:
            self.house_model = self.property_id.house_model.id
            self.county = self.property_id.county.id
            

    # @api.constrains('property_id')
    # def _check_property_on_hold(self):
    #     for record in self:
    #         if record.property_id and record.property_id.on_hold == True:
    #             raise ValidationError("The selected property is on hold. You cannot create a material order for this property.")

###########################################################################################################################################################################################################

    # Nueva funcion para enviar solo emails 

    def _send_email_to(self, email_addresses, html_content):
        if not email_addresses:
            return {
                'type': 'ir.actions.act_window',
                'name': 'No Email Wizard',
                'res_model': 'no.email.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'order_id': self.id}
            }
        else:
            email_to = ','.join(email_addresses)
            mail_values = {
                'subject': f'Order #{self.name} is waiting for confirmation',
                'body_html': html_content,
                'email_to': email_to,
            }
            self.env['mail.mail'].create(mail_values).send()
            
    # Nueva funcion para enviar solo SMS 
    
    def _send_sms_messages(self, phone_numbers, message):

        access_token = self.env['sms.silvamedia'].search([], limit=1)

        for phone_number in phone_numbers:
            if not re.match(r'^\+1\d{10}$', phone_number):
                raise ValidationError("Phone number %s doesn't have a valid format." % phone_number)

            self.send_sms_message(phone_number, phone_number, message, access_token)

###########################################################################################################################################################################################################

    def go_back(self):
        redirect = {
            'type': 'ir.actions.act_url',
            'url': '/web',
            'target': 'self',
        }
        return redirect
    
    def view_orders(self):
        kanban_view = self.env.ref('create_material_orders.material_orders_view_kanban')
        employee_id = self._context.get('default_order_creator')
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
                # 'domain': [('order_creator', '=', employee_id)],
                'context': {
                    'default_order_creator': employee_id,
                    # 'search_default_waiting_conf': 1
                    }
            }
        return redirect
    
    #   name: 'Material Orders',
    #   type: 'ir.actions.act_window',
    #   res_model: 'pms.materials',
    #   views: [[false, 'tree']],
    #   target: 'fullscreen',
    #   context: {
    #   'default_order_creator': orderCreator,
    #   }
    #   });
    
    
    def create_order(self):
        same_order = self.env['pms.materials'].search([('property_id', '=', self.property_id.id),
                                                       ('template_id', '=', self.purchase_template.id),
                                                       ('template_id', '!=', False),])
        project = self.env['pms.projects'].search([('address', '=', self.property_id.id)])
        if same_order:
            raise UserError("There is already an order for this property with the same template.")
        elif self.property_id == False or self.house_model == False:
            raise UserError("Please select a property.")
        else:
            order_lines = []
            for line in self.order_wizard_lines:
                order_lines.append((0, 0, {
                    'product': line.product.id,
                    'subproduct': line.subproduct.id,
                    'unit_measure': line.unit_measure,
                    'quantity': line.quantity,
                    'amount': line.amount
                }))
            order = self.env['pms.materials'].sudo().create({
                'order_creator': self.order_creator.id,
                'property_id': self.property_id.id,
                'template_id': self.purchase_template.id if self.special_order == False else False,
                'order_creation_date': self.order_date,
                'order_status': 'not_ordered',
                'reference': self.purchase_template.name,
                'provider': self.purchase_template.provider.id,
                'material_lines': order_lines,
                'special_order': self.special_order
            })
            # order._send_email_to(self, ["a@a.com"], "order created")
            
            # Adds order creator as a follower
            # PENDING: add compradores y supervisor
            order.message_subscribe(partner_ids=[
                self.order_creator.id,
                project.project_manager.id,
                project.zone_coordinator.id,
                project.superintendent.id
                ])
            
            # PENDING: Send email and sms

            order.message_post(body=self.comments)
            # self._send_email_to(email_addresses, html_content)
            # self._send_sms_messages(phone_numbers, message)
            
            self.property_id = False
            self.house_model = False
            self.purchase_template = False
            self.order_date = self.get_current_date()
            self.ask_for_measure = False
            self.special_order = False
            self.comments = False
            self.order_wizard_lines = False
            self.order_wizard_lines_ro = False
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': "Order created successfully!", 'type': 'info', 'sticky': False, 'next': {'type': 'ir.actions.act_window_close'}}
            }
                
            
            

class CreateOrderWizardLine(models.TransientModel):
     _name = 'create.order.wizard.line'
     _description = 'Create Order Wizard Line'

     wizard_id = fields.Many2one('create.order.wizard', string='Wizard')
     product = fields.Many2one('product.product', string='Product')
     subproduct = fields.Many2one('product.subproduct', string='Subproduct')
     quantity = fields.Integer(string='Quantity', default=0)
     unit_measure = fields.Char(string='Unit of Measure')
     amount = fields.Float(string='Amount')
     total = fields.Float(string='Total', compute='_compute_total', store=True)

     @api.depends('quantity', 'amount')
     def _compute_total(self):
         for line in self:
             line.total = line.quantity * line.amount

class CreateOrderWizardLineReadonly(models.TransientModel):
     _name = 'create.order.wizard.line.ro'
     _description = 'Create Order Wizard Line Readonly'

     wizard_id_ro = fields.Many2one('create.order.wizard', string='Wizard', readonly=True)
     product = fields.Many2one('product.product', string='Product' , readonly=True)
     subproduct = fields.Many2one('product.subproduct', string='Subproduct', readonly=True)
     quantity = fields.Integer(string='Quantity', default=0, readonly=True)
     unit_measure = fields.Char(string='Unit of Measure', readonly=True)
     amount = fields.Float(string='Amount', readonly=True)
     total = fields.Float(string='Total', compute='_compute_total', store=True, readonly=True)

     @api.depends('quantity', 'amount')
     def _compute_total(self):
         for line in self:
             line.total = line.quantity * line.amount
