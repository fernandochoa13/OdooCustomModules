from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

class pms_units(models.Model):
    _name = 'pms.units'
    _description = 'Units'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Unit Name', required=True, tracking=True)
    property_address = fields.Many2one('pms.property', string='Property Address', required=True, tracking=True)
    # vacant = fields.Boolean(string='Vacant', default=False, tracking=True) # QUITAR?
    
    # RENT DASHBOARD FIELDS
    
    status = fields.Selection([('occupied', 'Occupied'), ('vacant', 'Vacant'), ('eviction', 'Eviction')], string='Property Status', tracking=True)
    rent = fields.Float(string='Rent', required=True, tracking=True)

