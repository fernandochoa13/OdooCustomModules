# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_property_type = fields.Selection(related='website_id.website_property_type', readonly=False)
