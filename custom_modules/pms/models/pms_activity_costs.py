import base64
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta, datetime
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch
from odoo.tools.misc import clean_context, format_date
from odoo import http
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
import io
import zipfile
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action
from werkzeug import urls

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
import base64
import collections
import datetime
import hashlib
import pytz
import threading
import re

import requests
from collections import defaultdict
from random import randint
from werkzeug import urls

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.osv.expression import get_unaccent_wrapper
from odoo.exceptions import RedirectWarning, UserError, ValidationError

class PMSActivityCosts(models.Model):
    _name = "pms.activity.costs"
    _description = "Activity Costs"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Activity Name", required=True)