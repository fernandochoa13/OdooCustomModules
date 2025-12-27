from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    third_party_company_id = fields.Many2one('res.company', string='Default Third Party Company', config_parameter="pms.third_party_company_id", default_model="pms")
    markup = fields.Float(string='Default Markup (%)', default=0.0, default_model="pms", config_parameter="pms.markup") # default_mode -> default_model
