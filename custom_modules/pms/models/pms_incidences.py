from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class pms_incidence(models.Model):
    _name = 'pms.incidence'
    _description = 'PMS Incidence'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Subject', required=True, copy=False)
    description = fields.Html(string='Description', required=True, help="Detailed description of the incidence.")
    date_reported = fields.Datetime(string='Date Reported', default=fields.Datetime.now, readonly=True)
    reported_by_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, readonly=True)
    category_id = fields.Many2one('pms.incidence.category', string='Category', help="Categorize the incidence (e.g., Bug, Feature Request, Support).")
    status = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], string='Status', default='new', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Critical')
    ], string='Priority', default='1', tracking=True)
    assigned_to_id = fields.Many2one('res.users', string='Assigned To', help="User responsible for resolving this incidence.")
    resolution_notes = fields.Text(string='Resolution Notes', help="Notes on how the incidence was resolved.")

    def action_set_in_progress(self):
        self.ensure_one()
        self.write({'status': 'in_progress'})

    def action_set_resolved(self):
        self.ensure_one()
        self.write({'status': 'resolved'})
        
    def _send_message_to_channel(self):
        """
        Sends a message to a specific mail channel when a new incidence is created.
        This method is called by the automated action.
        """
        self.ensure_one()

        channel_found = self.env['mail.channel'].sudo().search([('name', '=', 'Incidences')], limit=1)
        if not channel_found:
            channel_found = self.env['mail.channel'].sudo().create({
                'name': 'Incidences',
                'channel_type': 'channel',
            })
        channel = channel_found
        if channel:
            message_body = f"A new incidence has been reported: <a href='#model=pms.incidence&amp;id={self.id}'>{self.name}</a>"
            
            channel.sudo().message_post(
                body=message_body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            message = f'Incidence report "{self.name}" has been notified to the Incidences Channel.'
            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                    'type': 'danger',
                    'title': _("New Incidence Reported"),
                    'message': message,
                    'sticky': False
                })
        else:
            message = f'Channel not found. Incidence report "{self.name}" has not been notified.'
            return self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'danger',
                'title': _("Error"),
                'message': message,
                'sticky': False
            })
    
class pms_incidence_category(models.Model):
    _name = 'pms.incidence.category'
    _description = 'Incidence Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The category name must be unique !')
    ]