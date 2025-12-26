from odoo import models, fields


class EventEvent(models.Model):
    _inherit = [
        "event.event",
    ]
    _name = 'event.event'
