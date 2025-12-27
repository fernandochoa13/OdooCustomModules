from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference
import ast
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache
import requests
import json
#from intuitlib.exceptions import AuthClientError
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action
from datetime import date, timedelta
from odoo import api, models, fields
from odoo.tools import SQL
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
from odoo.fields import Command
from datetime import date
import base64
import io
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict
import math
import re
import string

class InternalPurchases(models.Model):
    _name = "internal.purchases"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _description = "Internal Purchases"

    name = fields.Char(string='Name', store=True)
    property_name = fields.Many2one('pms.property', string='Property', required=True)
    property_model = fields.Many2one(related='property_name.house_model', string='Model', readonly=True)
    property_owner = fields.Many2one(related='property_name.partner_id', string='Owner', readonly=True)
    property_zone = fields.Char( string='Zone')
    paint = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Paint')
    tile = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string="Tile")
    floors = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Floors')
    cabinets = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Cabinets')
    accessories = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Accessories')
    lamps = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Lamps')
    locks = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Locks')
    provisional_lock = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Provisional Lock')
    final_lock = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Final Lock')
    house_numbers = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='House Numbers')
    garbage_disposal_button = fields.Selection(selection=[("done","Done"), ("request", "Request"), ("in_delivery", "Awaiting Delivery"), ("purchased", "Purchased")], default="", string='Garbage Disposal Unit Button')

