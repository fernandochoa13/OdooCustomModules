from odoo import api, fields, models, _

class crm_lead(models.Model):
    _inherit = "crm.lead"
    
    property_id = fields.Many2one('pms.property', string="Property")
    
    request_open_date = fields.Datetime(string="Request Open Date", copy=False)
    request_close_date = fields.Datetime(string="Request Close Date", copy=False)
    
    # has_capital = fields.Selection([('yes', 'Yes'), ('have_10', 'No'), ('no', 'No')], string="Has Capital?", default='no')
    
    # city_of_interest = fields.Char(string="City of Interest")
    # city_of_interest_advice = fields.Char(string="City of Interest Advice")
    # city_of_interest_construction = fields.Selection([('port_fl', 'Port Charlotte'), ('ocala_fl', 'Ocala'),  ('sebring_fl', 'Sebring'),  ('advice', '|Advice')], string="City of Interest Construction?")
    
    # interest = fields.Selection([('build', 'Build'), ('buy', 'Buy'), ('acquire', 'Acquire'), ('invest', 'Invest'), ('invest_real', 'Invest Real')], string="Interest")
    # pre_approved = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Pre-Approved?", default='no')