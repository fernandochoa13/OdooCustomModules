from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch

from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference


class SaleOrders(models.Model):
    _inherit = ["sale.order"]

    # Editable fields for invoice/quotation notes and terms
    estimate_notes = fields.Html(
        string="Estimate Notes",
        help="Custom notes to display at the bottom of the estimate/quotation. Supports HTML formatting."
    )
    scope_of_work = fields.Html(
        string="Scope of Work",
        help="Scope of work and terms to display on the estimate. Supports HTML formatting."
    )
    
    @api.model
    def _get_default_scope_of_work(self):
        """Returns the default scope of work text"""
        return """
        <div style="font-size: 9pt;">
            <p><strong>Scope of Work and Unforeseen Conditions</strong></p>
            <p>The Client acknowledges that the scope of work in this estimate is based solely on visible conditions and the information available at the time of assessment.</p>
            <p>If concealed or unforeseen conditions arise during the project, we reserve the right to modify the project scope, schedule, and pricing as necessary.</p>
            <p>No work beyond the original scope will proceed without the Client's approval.</p>
            
            <p><strong>Additional Costs and Adjustments</strong></p>
            <p>The rates listed for common unforeseen repairs are estimates only. Final costs shall be determined based on actual conditions encountered.</p>
            
            <p><strong>Method of Payment</strong></p>
            <ul>
                <li>An initial payment of fifty percent (50%) of the total contract price is due prior to commencing work.</li>
                <li>A second payment of twenty-five percent (25%) is due upon completion of the dry-in stage.</li>
                <li>The remaining twenty-five percent (25%) is due immediately upon final completion of the project.</li>
            </ul>
            
            <p><strong>Warranty</strong></p>
            <p>We warrant our labor for a period of five (5) years from the date of final completion, limited to defects in workmanship.</p>
            
            <p>This estimate remains valid for thirty (30) days from the date of issuance.</p>
        </div>
        """

    def action_cancel_button(self):
            self._action_cancel()
            """ Cancel SO after showing the cancel wizard when needed. (cfr :meth:`_show_cancel_wizard`)

            For post-cancel operations, please only override :meth:`_action_cancel`.

            note: self.ensure_one() if the wizard is shown.
            """
            '''for record in self:
                cancel_warning = record._show_cancel_wizard()
                if cancel_warning:
                    template_id = record.env['ir.model.data']._xmlid_to_res_id(
                        'sale.mail_template_sale_cancellation', raise_if_not_found=False
                    )
                    lang = record.env.context.get('lang')
                    template = record.env['mail.template'].browse(template_id)
                    if template.lang:
                        lang = template._render_lang(record.ids)[record.id]
                    ctx = {
                        'default_use_template': bool(template_id),
                        'default_template_id': template_id,
                        'default_order_id': record.id,
                        'mark_so_as_canceled': True,
                        'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
                        'model_description': record.with_context(lang=lang).type_name,
                    }
                    return {
                        'name': _('Cancel %s', record.type_name),
                        'view_mode': 'form',
                        'res_model': 'sale.order.cancel',
                        'view_id': record.env.ref('sale.sale_order_cancel_view_form').id,
                        'type': 'ir.actions.act_window',
                        'context': ctx,
                        'target': 'new'
                    }
                else:'''
        
