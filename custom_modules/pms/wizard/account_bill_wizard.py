from odoo import models, fields, api

class account_bill_wizard(models.TransientModel):
    _name = 'account.bill.wizard'
    _description = 'Bills Wizard'

    def ignore_duplicate(self):
        ctx = self.env.context.get('dup_id')
        self.env['account.move'].browse(ctx).action_post()
        return {'type': 'ir.actions.act_window_close'}
    

    def cancel_bill(self):
        return {'type': 'ir.actions.act_window_close'}

    # def view_similar_bills(self):
    #     ctx = self.env.context.get('bill_ids')
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': ('view_invoice_tree'),
    #         'res_model': 'account.move',
    #         'view_type': 'tree',
    #         'view_mode': 'tree',
    #         'domain': [('id', 'in', ctx)]
    #     }
    

    def view_similar_bills(self):
        ctx = self.env.context.get('bill_ids')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Similar Bills',
            'res_model': 'bill.report',
            'view_mode': 'tree',
            'domain': [('id', 'in', ctx)],
            'view_id': self.env.ref('pms.view_bill_report_tree').id
        }