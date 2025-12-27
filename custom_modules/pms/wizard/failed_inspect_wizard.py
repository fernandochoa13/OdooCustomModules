from odoo import models, fields, api

class failed_inspect_wizard(models.TransientModel):
    _name = 'failed.inspect.wizard'
    _description = 'Failed Inspection Wizard'

    fail_reason = fields.Text(string="Fail Reason", readonly=False, default='')

    
    def cancel(self):
        ctx = self.env.context.get('insp_id')
        self.env['pms.inspections'].browse(ctx).write({'status': 'ordered'})
        return {'type': 'ir.actions.act_window_close'}
    
    def failed_inspect(self):
        ctx = self.env.context.get('insp_id')
        insp = self.env['pms.inspections'].browse(ctx)
        inspection = {
            'fail_reason': self.fail_reason,
            'status': 'failed',
            'fail_counter': insp.fail_counter + 1,
        }
        insp.write(inspection)
        
        var = {
            'failure_number': insp.fail_counter + 1,
            'fail_reason': self.fail_reason,
            'fail_date': fields.Date.today(),
            'inspection_id': insp.id
        }
        self.env['pms.inspections.failures'].create(var)

        note = f'''
            <div style="background-color: #FFEBEE; color: #B71C1C; padding-left: 20px; padding-top:10px; padding-right: 20px; padding-bottom: 10px; margin-top: 10px; margin-bottom: 10px; border-radius: 10px; border: 1px solid #E53935;">
                <span style="font-size: 1.2em; font-weight: bold;">Inspection Failed</span><br>
                <i><b>Reason:</b> {self.fail_reason}</i>
            </div>
        '''
        insp.message_post(body=note)
        
        return {'type': 'ir.actions.act_window_close'}