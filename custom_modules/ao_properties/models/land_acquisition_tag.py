from odoo import models, fields


class LandAcquisitionTag(models.Model):

    _name = 'land.acquisition.tag'
    _description = 'Land Acquisition Tag'

    name = fields.Char(string="Name")
    color = fields.Integer(string="Color")
