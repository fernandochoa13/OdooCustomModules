from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

class pms_projects_routes_templates(models.Model):
    _name = "pms.projects.routes.templates"
    _description = "Table for Property Project Management Routes Templates"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Route Name")
    house_model = fields.Many2one("pms.housemodels", string="House Model")
    route_lines = fields.One2many("pms.projects.routes.templates.lines", "route_header", string="activity")
    default_job_name = fields.Many2one("product.product", string="Default Job Name", store=True)
    active = fields.Boolean(default=True, string="Active*")
    
class pms_projects_routes_templates_lines(models.Model):
    _name = "pms.projects.routes.templates.lines"
    _description = "Table for Property Project Management Routes Templates Lines"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Activity Name")
    product = fields.Many2one("product.product", string="Job Name")
    activity = fields.Many2one("pms.activity.costs", string="Activity")
    predecessor = fields.Many2many("pms.projects.routes.templates.lines", "pms_projects_routes_templates_lines_predecessor_rel", "route_line_id", "predecessor_id", string="Predecessor")
    activity_type = fields.Selection(selection=[("job", "Job"), ("payment", "Payment"), ("inspection", "Inspection")])
    duration = fields.Integer(string="Work Days")
    phase = fields.Selection(selection=[
        ("epp", "EPP"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("ppa", "PPA"),
        ("cop", "COP"),
        ("cop1", "COP1"),
        ("cop2", "COP2"),
        ("cop3", "COP3"),
        ("cop4", "COP4"),
        ("coc", "COC")
        ], string="Construction Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='pps')
    sequence = fields.Integer(string="Sequence")
    vendor = fields.Many2one("res.partner", string="Contractor", domain="[('company_id', '=', False)]")
    company_id = fields.Many2one("res.company", string="Company", required=False)
    route_header = fields.Many2one("pms.projects.routes.templates", string="Route")
    acronym = fields.Char(string="Acronym")
    alert = fields.Boolean(string="Alert Sequence")
    alert_type = fields.Selection(selection=[("own", "Own"), ("third", "Third Party"), ("both", "Both")], string="Alert Type")
    inspection_type = fields.Many2one("pms.inspections.type", string="Inspection Type", required=False)
    # New boolean to add to report
    add_to_report = fields.Boolean(string="Add to Report", default=False, required=False)
    active = fields.Boolean(default=True, string="Active")
    x_active = fields.Boolean(related="route_header.active", string="Active*", store=True)
    