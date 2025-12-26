from odoo import models, fields


class LandAcquisitionStage(models.Model):

    _name = 'land.acquisition.stage'
    _description = 'Land Acquisition Stage'

    name = fields.Char(string="Name")
    sequence = fields.Integer(string="Sequence")
