import logging
import re

from binascii import Error as binascii_error
from odoo import _, api, fields, models, modules, tools
from odoo.http import request
from binascii import Error as binascii_error
from collections import defaultdict
from odoo.exceptions import AccessError, UserError, ValidationError
from operator import itemgetter
from odoo.tools.misc import clean_context
import requests

class Connector(models.Model):
    _name = 'whatsapp.connector'
    
    url = fields.Char(string='URL')


class WhatsappTemplates(models.Model):
    _name = 'whatsapp.templates'
    
    name = fields.Char(string='Name')
    body = fields.Text(string='Body')




class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def action_send_whatsapp_message(self):
        """ Action to send a whatsapp message """
        partners_ids = self.ids
        if not partners_ids:
            raise UserError(_('Please select at least one partner'))
        
        context = {'partners_ids': partners_ids}

        view_id = self.env.ref('whatsapp_connector.view_send_ws_message_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'send.ws.message.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': context,
        }

    
    # This function is gonna send the whatsapp message itself to the partner
    def _send_wa_message(self, message, partner_id, url):
        """ Send a message through whatsapp """
        self.ensure_one()
        
        phone = self.env['res.partner'].browse(partner_id).phone
        if not phone:
            raise UserError(_('No phone number configured for this partner'))
        
        # Strip '-' and spaces from phone number
        phone = phone.replace('-', '').replace(' ', '').replace('+', '')

        # Send the message
        url = url + f'?p={phone}&b={message}'

        try:
            response = requests.get(url)
        except requests.exceptions.RequestException as e:
            raise UserError(_('Error sending the message: %s') % e)
        
        if response.status_code != 200:
            raise UserError(_('Error sending the message: %s') % response.text)
        
        # Log a note with the message
        self.env['mail.message'].create({
            'model': 'res.partner',
            'res_id': partner_id,
            'message_type': 'comment',
            'body': message,
        })

    def prepare_ws_template_message(self, body):
        """ Prepare the message to send through whatsapp """
        self.ensure_one()
        # Replace variables in the body
        body = body.replace('%PARTNER_NAME%', self.name)
        body = body.replace('%PARTNER_EMAIL%', self.email)
        body = body.replace('%PARTNER_PHONE%', self.phone)
        body = body.replace('%PARTNER_MOBILE%', self.mobile)
        body = body.replace('%OVERDUE%', str(self.total_overdue))
        invoices = self.unpaid_invoice_ids
        invoice_names = '\n'.join(invoices.mapped('name'))
        body = body.replace('%INVOICES%', invoice_names) 
        invoices_portal_links = '\n \n'.join(invoices.mapped(lambda inv: f'{inv.name} \n {inv.get_portal_url()}'))
        body = body.replace('%INVOICES_PORTAL_LINKS%', invoices_portal_links)


        return body

    def send_followup_ws(self, options):
        """ Send a followup message through whatsapp """
        for record in self:
            followup = options.get('followup_line')
            body_content = followup.whatsapp_template_id.body
            message = record.prepare_ws_template_message(body_content)
            url = record.env['whatsapp.connector'].search([], limit=1).url
            # Send the message
            record._send_wa_message(message, self.id, url)

    def _send_followup(self, options):
        """ Send the follow-up to the partner, depending on selected options.
        Can be overridden to include more ways of sending the follow-up.
        """
        self.ensure_one()
        followup_line = options.get('followup_line')
        if options.get('email', followup_line.send_email):
            self.send_followup_email(options)
        if options.get('sms', followup_line.send_sms):
            self.send_followup_sms(options)
        if options.get('followup_line').send_whatsapp:
            self.send_followup_ws(options)