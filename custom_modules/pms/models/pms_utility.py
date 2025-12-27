from odoo import api, models, fields
from odoo.exceptions import ValidationError

class pms_utility(models.Model):
    _name = "pms.utility"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Utilities per company"
    
    name = fields.Char(required=True, string="Work Order")
    property_address = fields.Many2one("pms.property", string="Property Address", required=True)
    utility_county = fields.Many2one(related = "property_address.county", string="Utility County")
    utility_parcel_id = fields.Char(related = "property_address.parcel_id", string="Utility Parcel ID")
    utility_model = fields.Many2one(related = "property_address.house_model", string="Utility Model")
    utility_phase = fields.Selection(related="property_address.projects.status_construction", string="Construction phase", copy=False, index=True, tracking=True, readonly=True) # redundant default: default='pps'
    utility_type = fields.Selection(selection=[
        ("water", "Water"),
        ("electrical", "Electrical"),
        ("sewage", "Sewage"),
        ], string="Utility Type",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    app_date = fields.Date(string="Application Date")
    conn_type = fields.Selection(selection=[
        ("underground", "Underground"),
        ("overhead", "Overhead"),
        ], string="Electrical Connection Type",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    water_conn_type = fields.Selection(selection=[
        ("well_pump", "Well Pump"),
        ("city_water", "City Water"),
        ], string="Water Connection Type",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    invoice = fields.Boolean(string="Is invoice paid?")
    elect_meter = fields.Boolean(string="Electric Meter")
    utlity_provider = fields.Many2one("res.partner", string="Utility Provider")
    elect_meter_position = fields.Selection(selection=[
        ("left", "Left"),
        ("right", "Right"),
        ], readonly=False, copy=False, index=True, tracking=True,
        default='', string="Electric Meter Position")
    elect_meter_request = fields.Boolean(string="Electric Meter Request")
    water_connection_request = fields.Boolean(string="Water Connection Request")
    conn_status = fields.Selection(
        selection=[
            ('disconnected', "Disconnected"),
            ('connected', "Connected")
        ],
        string="Connection Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='disconnected')
    comments = fields.Char(string="Comments")
    conn_date = fields.Date(string="Connection Date")
    elect_meter_request_date = fields.Date(string="Electric Meter Request Date")
    payment_date = fields.Date(string="Payment Date")
    elect_utility_engineer = fields.Many2one("res.partner", string="Electric Utility Engineer")
    disconn_date = fields.Date(string="Disconnection Date")
    sunshine = fields.Text(string="Sunshine")
    
    def get_utilities_payments(self):
        self.ensure_one()
        vendor = self.utility_vendor.id
        analytic_account_id = self.property_address.analytical_account.id
        return {
        'type': 'ir.actions.act_window',
        'name': ('view_account_analytic_line_tree'),
        'res_model': 'account.analytic.line',
        'domain':[("partner_id.id", "=", vendor), ("account_id.id", "=", analytic_account_id)],
        'view_mode': 'tree'}


    def connect(self):
        self.conn_status = "connected"
        self.disconn_date = False

    
    def disconnect(self):
        self.conn_status = "disconnected"
    #report to see last payments
    #button to register batch payment


    
    # === Documents functions to override === #
    def _get_document_folder(self):
        return self.env["documents.folder"].search([("name", "=", "Properties")])





    