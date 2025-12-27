# from collections import defaultdict
# from contextlib import ExitStack, contextmanager
# from datetime import date, timedelta
# from hashlib import sha256
# from json import dumps
# import re
# from textwrap import shorten
# from unittest.mock import patch
# from odoo.tools.misc import clean_context, format_date

# from odoo import api, fields, models, _, Command
# from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference
# import ast
# from collections import defaultdict
# from contextlib import contextmanager
# from datetime import date, timedelta
# from functools import lru_cache
# import requests
# import json
# #from intuitlib.exceptions import AuthClientError

# from odoo import api, fields, models, Command, _
# from odoo.exceptions import ValidationError, UserError
# from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
# from odoo.tools.sql import create_index
# from odoo.addons.web.controllers.utils import clean_action

# from odoo.addons.account.models.account_move import MAX_HASH_VERSION

# # -*- coding: utf-8 -*-
# from odoo import api, fields, models, _, Command
# from odoo.osv import expression
# from odoo.tools.float_utils import float_round
# from odoo.exceptions import UserError, ValidationError
# from odoo.tools.misc import formatLang
# from odoo.tools import frozendict

# from collections import defaultdict
# import math
# import re
# import string


# TYPE_TAX_USE = [
#     ('sale', 'Sales'),
#     ('purchase', 'Purchases'),
#     ('none', 'None'),
# ]

# class AccountReconcile(models.Model):
#     _inherit = ["account.reconcile.model"]

#     rule_type = fields.Selection(selection=[
#         ('writeoff_button', 'Button to generate counterpart entry'),
#         ('writeoff_suggestion', 'Rule to suggest counterpart entry'),
#         ('invoice_matching', 'Rule to match invoices/bills'),
#         ('check_matching', 'Rule to match checks'),
#     ], string='Type', default='writeoff_button', required=True, tracking=True)

#     def _apply_rules(self, st_line, partner):
#             ''' Apply criteria to get candidates for all reconciliation models.

#             This function is called in enterprise by the reconciliation widget to match
#             the statement line with the available candidates (using the reconciliation models).

#             :param st_line: The statement line to match.
#             :param partner: The partner to consider.
#             :return:        A dict mapping each statement line id with:
#                 * aml_ids:          A list of account.move.line ids.
#                 * model:            An account.reconcile.model record (optional).
#                 * status:           'reconciled' if the lines has been already reconciled, 'write_off' if the write-off
#                                     must be applied on the statement line.
#                 * auto_reconcile:   A flag indicating if the match is enough significant to auto reconcile the candidates.
#             '''
#             available_models = self.filtered(lambda m: m.rule_type != 'writeoff_button').sorted()

#             for rec_model in available_models:

#                 if not rec_model._is_applicable_for(st_line, partner):
#                     continue

#                 if rec_model.rule_type == 'invoice_matching':
#                     rules_map = rec_model._get_invoice_matching_rules_map()
#                     for rule_index in sorted(rules_map.keys()):
#                         for rule_method in rules_map[rule_index]:
#                             candidate_vals = rule_method(st_line, partner)
#                             if not candidate_vals:
#                                 continue

#                             if candidate_vals.get('amls'):
#                                 res = rec_model._get_invoice_matching_amls_result(st_line, partner, candidate_vals)
#                                 if res:
#                                     return {
#                                         **res,
#                                         'model': rec_model,
#                                     }
#                             else:
#                                 return {
#                                     **candidate_vals,
#                                     'model': rec_model,
#                                 }
#                 elif rec_model.rule_type == 'check_matching':
#                         label = st_line.payment_ref
#                         label = label.lower()
#                         check_regex = r'check.*\d+|\d+.*check'
#                         check_number = re.search(check_regex, label)
#                         if check_number is None:
#                             return {}
#                         else:
#                             label_number = ''.join(i for i in label if i.isdigit() or i in '-./\\')
#                             candidate = self.env["account.payment"].search(["&",
#                                 ('check_number', '=', label_number),
#                                 #('move_id.company_id', '=', st_line.move_id.company_id),
#                                 ('state', 'in', ['posted', 'sent'])
#                             ])

#                             if candidate:            
#                                 if len(candidate.ids) > 1:
#                                     return {}
#                                 else:
#                                     line  = candidate.move_id.line_ids.filtered(lambda l: l.credit > 0)
#                                     """if line.reconciled:
#                                         return {}"""
#                                     if len(line.ids) == 1:
#                                         check = {
#                                             'amls': line,
#                                             'status': "write_off",
#                                             'auto_reconcile': True,
#                                         }
#                                         return {
#                                             **check,
#                                             'model': rec_model,
#                                         }
                            
#                             else:
#                                 return {}
#                 elif rec_model.rule_type == 'writeoff_suggestion':
#                     return {
#                         'model': rec_model,
#                         'status': 'write_off',
#                         'auto_reconcile': rec_model.auto_reconcile,
#                     }
#             return {}