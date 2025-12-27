from odoo import models, fields, api

class pms_orderjobs_wizard(models.TransientModel):
    _name = 'pms.orderjobs.wizard'
    _description = 'Order Jobs Wizard'

    vendor_id = fields.Many2one('res.partner', string='Vendor')

    def open_order_jobs(self):
        res_ids = self.env.context.get('active_ids')
        reccordss = self.env["pms.projects.routes"].search([('id', '=', res_ids)])
        reccordss.sudo().write({'vendor': self.vendor_id.id})
        
