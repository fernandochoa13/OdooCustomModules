from odoo import api, models, tools, fields

class processes_general_report(models.Model):
    _name="pms.processes.general.report"
    _description="Processes General Report"
    _auto = False
    
    owner_property = fields.Many2one('res.partner', string = "Property Owner", readonly = True)
    address_id = fields.Many2one('pms.property', string="Address", readonly=True)
    maturity_date = fields.Date(string="Expiration Date", readonly=True)
    elect_meter = fields.Boolean(string="Electric Meter", readonly=True)
    
    expected_co_date = fields.Date(string="Expected CO Date", readonly=True)
    
    own_third_property = fields.Selection(readonly=True, selection=[("own", "Own"), ("third", "Third Party")])
    construction_status = fields.Selection(string="Construction Status", readonly=True, selection=[
        ("pending", "Pending"), ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"), ("pip", "PIP"), ("pps", "PPS"),
        ("ppa", "PPA"), ("cop", "COP"), ("cop1", "COP1"), ("cop2", "COP2"), ("cop3", "COP3"), ("cop4", "COP4"), ("cop5", "COP5"),
        ("coc", "COC"), ("completed", "Completed")])
    
    