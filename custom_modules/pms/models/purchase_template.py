from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class PurchaseTemplate(models.Model):
    _name = "purchase.template"
    _description = "Purchase Template"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Template Name')
    house_model = fields.Many2many('pms.housemodels', string='House Model')
    county = fields.Many2many('pms.county', string='Template County')
    provider = fields.Many2one('res.partner', string='Provider')
    ask_for_measurement = fields.Boolean(string='Ask for Measurement')
    template_lines = fields.One2many('purchase.template.lines', 'purchase_template_id', string='Template Lines')
    template_lines_total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount')

    @api.depends('template_lines')
    def _compute_total_amount(self):
        for record in self:
            record.template_lines_total_amount = sum(record.template_lines.mapped('total'))

    def action_add_county(self):
        return {
            'name': 'Add County',
            'view_mode': 'form',
            'res_model': 'purchase.template.add.county',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

class PurchaseTemplateLines(models.Model):
    _name = "purchase.template.lines"
    _description = "Purchase Template Lines"

    purchase_template_id = fields.Many2one('purchase.template', string='Purchase Template')
    product = fields.Many2one('product.product', string='Product')
    subproduct = fields.Many2one('product.subproduct', string='Subproduct')
    quantity = fields.Integer(string='Quantity')
    unit_measure = fields.Char(string='Unit of Measure')
    amount = fields.Float(string='Amount')
    total = fields.Float(string='Total', compute='_compute_total')

    @api.depends("quantity", "amount")
    def _compute_total(self):
        for record in self:
            record.total = record.quantity * record.amount
            
            
class purchase_template_add_county(models.TransientModel):
    _name = "purchase.template.add.county"
    _description = "Purchase Template Add County"
    
    county = fields.Many2many('pms.county', string='Template County')
    
    def add_county(self):
        purchase_template_ids = self.env.context.get('active_ids', [])

        if purchase_template_ids:
            purchase_templates = self.env['purchase.template'].browse(purchase_template_ids)
            county_count = len(self.county)
            template_count = len(purchase_templates)

            for template in purchase_templates:
                template.county = [(4, county.id, 0) for county in self.county]

            if county_count == 1 and template_count == 1:
                county_name = self.county.name
                message = _("County '%s' successfully added to %d purchase template.") % (county_name, template_count)
            elif county_count == 1:
                county_name = self.county.name
                message = _("County '%s' successfully added to %d purchase templates.") % (county_name, template_count)
            elif template_count == 1:
                county_names = ", ".join(self.county.mapped('name'))
                message = _("Counties '%s' successfully added to %d purchase template.") % (county_names, template_count)
            else:
                county_names = ", ".join(self.county.mapped('name'))
                message = _("Counties '%s' successfully added to %d purchase templates.") % (county_names, template_count)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'info',
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'}
                }
            }