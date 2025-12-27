from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class pms_request_draw_wizard(models.TransientModel):
    _name = 'pms.request.draw.wizard'
    _description = 'Request Draw Wizard'

    draw_ref = fields.Char(string='Draw Ref')

    def open_request_draw(self):
        
        res_ids = self.env.context.get('active_ids')

        reccordss = self.env["pms.projects"].search([('id', '=', res_ids)])
        

        if reccordss.address.loans:
            status_draw = reccordss.address.loans.search(["&", ("exit_status", "!=", "refinanced"), ("property_address", "=", reccordss.address.id)])
            if isinstance(status_draw.ids, list) and len(status_draw.ids) > 1:
                raise ValidationError("The property has more than one active loan. Please select the loan to request the draw.") 
            else:
                    draw_draft = {
                        'name': self.draw_ref,
                        'loan_id': status_draw.id,
                        'draw_amount': '',
                        'draw_fee': '',
                        'memo': '',
                        'date': datetime.now(),
                        'status': 'draft'
                        }
                    
                    self.env["pms.draws"].create(draw_draft)
        else:    
            raise ValidationError("The property does not have a loan associated with it.")
        




        
    