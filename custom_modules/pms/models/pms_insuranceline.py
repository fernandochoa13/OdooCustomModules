from odoo import api, models, fields

class pms_insuranceline(models.Model):
    _name = 'pms.insuranceline'
    _description = 'Insurance Line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Buildings")
    properties_associates = fields.Many2one("pms.property", string="Property Address")
    coverage_amount = fields.Monetary(string="Coverage Amount", currency_field='company_currency_id')
    premiun_amount = fields.Monetary(string="Premiun Amount", currency_field='company_currency_id')
    insurance_header = fields.Many2one("pms.insurance", string="Insurance Name")
    insurance_types = fields.Selection(related="insurance_header.insurance_type", readonly=True, required=False)
    
    policy_number = fields.Char(related="insurance_header.name", string="Policy Number")
    insurance_policy_end_date = fields.Date(related="insurance_header.insurance_end", string="Insurance Policy End Date")
    days_to_expire = fields.Float(related="insurance_header.days_to_expire", string="Days to expire")
    insurance_agent = fields.Many2one(related="insurance_header.insurance_agent", string="Insurance Agent")
    open_claim = fields.Boolean(related="insurance_header.open_claim", string="Open Claim")
    # === Currency fields === #
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Accounting Company',
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True
    )
