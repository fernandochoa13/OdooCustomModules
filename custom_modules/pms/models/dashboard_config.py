from odoo import api, models, fields
from odoo.exceptions import ValidationError



class dashboard_config(models.Model):
    _name = 'dashboard.config'
    _description = "Dashboard Config"

    name = fields.Char(string="Name of config", required=True)
    url = fields.Char(string="Base Url of dashboard server", required=True)
    secret_key = fields.Char(string="Secret Key", required=True)

