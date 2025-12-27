from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

class PMSOnHoldHistory(models.Model):
    _name = "pms.on.hold.history"
    _description = "Table for On Hold Properties History" 
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    property_name = fields.Many2one("pms.property", string="Property", required=True)
    county = fields.Many2one(related="property_name.county", string="County", store=True)
    property_owner = fields.Many2one(related="property_name.partner_id", string="Property Owner")
    hold_by_owner = fields.Boolean(string="Hold by Owner", store=True, readonly=True)
    date = fields.Date(string="Date")
    responsible = fields.Many2one("hr.employee", string="Responsible")
    mail_notification = fields.Boolean(string="Mail Notification")
    previous_status = fields.Selection(selection=[
        ("pending", "Pending"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("epp", "EPP"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("ppa", "PPA"),
        ("cop", "COP"),
        ("cop1", "COP1"),
        ("cop2", "COP2"),
        ("cop3", "COP3"),
        ("cop4", "COP4"),
        ("coc", "COC"),
        ("completed", "Completed"),
        ], string="Construction Status",
        readonly=False, copy=False, index=True, tracking=True,
        default='pending')
    comments = fields.Text(string="Comments")
    jennys_calls = fields.Boolean(string="Jenny's Calls")
    hold_end_date = fields.Datetime(string="On Hold End Date")
    off_hold_reason = fields.Text(string="Off Hold Reason")

    invoice_ids = fields.Many2many('account.move', string='Related Invoices')
    product_ids = fields.Many2many(
        'product.product',
        string="Related Products",
        help="Products associated with the overdue invoices that caused the property to be put on hold."
    )
    
    # mail_sent = fields.Boolean(string="Mail Sent", default=False, help="Indicates if the mail notification has been sent.")
    # set_off_hold = fields.Boolean(string="Property Set Off Hold", default=False, help="Indicates if this property was manually set off hold from this record.")
    
    # def set_property_off_hold(self):
    #     for record in self:
    #         property = record.property_name
    #         if not property:
    #             raise ValidationError("Property must be specified.")
    #         property.put_off_hold()
    #         record.set_off_hold = True
    
    def manual_hold_email(self):
        for record in self:
            customer = record.property_owner
            property_address = record.property_name
            invoices_og = record.env['account.move'].search([('partner_id', '=', customer.id), 
                                    ('payment_state', '=', 'not_paid'), 
                                    ('move_type', '=', 'out_invoice'),
                                    ('state', '=', 'posted')])
            invoices_lines = invoices_og.line_ids.filtered_domain([('analytic_distribution', '=', {str(property_address.analytical_account.id): 100.0})])
            invoices = invoices_og.browse(invoices_lines.move_id.ids)

            html_content = f'''
            <h2 style="font-family:Arial;">Querido {customer.name},</h2>
                <p style="font-family:Arial;">Estimado/a {customer.name}
            Por este medio, se informa que el proyecto en construcción será puesto en hold hasta que los pagos pendientes sean realizados.

            A continuación, detallo las facturas pendientes:</p>
            '''      
            html_content += f'<h2 style="font-family:Arial;">Unpaid Invoices for {customer.name}</h2>'
            overall_total = 0
            html_content += f'<h3 style="font-family:Arial;">{property_address.name}</h3>'
            html_content += '''
                <table border="1" style="width:100%; border-collapse: collapse;">
                    <tr>
                        <th><a style="font-family:Arial;">Invoice Number</a></th>
                        <th>I<a style="font-family:Arial;">nvoice Reference</a></th>
                        <th><a style="font-family:Arial;">Due Date</a></th>
                        <th><a style="font-family:Arial;">Amount</a></th>
                        <th><a style="font-family:Arial;">Payment Link</a></th>
                    </tr>
            '''
            property_total = 0
            for invoice in invoices:
                if invoice.company_id.name == '3rd Party':
                    if invoice.invoice_link_docs:
                        html_content += f'''
                            <tr>
                                <td> </td>
                                <td><a style="font-family:Arial;">{invoice.payment_reference}</a></td>
                                <td><a style="font-family:Arial;">{invoice.invoice_date_due}</a></td>
                                <td><a style="font-family:Arial;">${invoice.amount_total:,.2f}</a></td>
                                <td colspan="4" style="text-align:center;">
                                    <a href="{invoice.invoice_link_docs}" style="
                                        display: inline-block;
                                        background-color: #000000;
                                        border: 2px solid #1A1A1A;
                                        border-radius: 12px;
                                        box-sizing: border-box;
                                        color: #FFFFFF;
                                        cursor: pointer;
                                        font-family: Arial;
                                        font-size: 12px;
                                        font-weight: 600;
                                        line-height: normal;
                                        margin: 6;
                                        min-height: 40px;
                                        outline: none;
                                        padding: 12px 18px;
                                        text-align: center;
                                        text-decoration: none;
                                        transition: all 300ms cubic-bezier(.23, 1, 0.32, 1);
                                        user-select: none;
                                        width: 80%;
                                        -webkit-user-select: none;
                                        touch-action: manipulation;
                                        will-change: transform;
                                    "><strong>PAY NOW</strong></a>
                                </td>
                            </tr>
                        '''
                        property_total += invoice.amount_total
                    else:
                        html_content += f'''
                            <tr>
                                <td></td>
                                <td><a style="font-family:Arial;">{invoice.payment_reference}</a></td>
                                <td><a style="font-family:Arial;">{invoice.invoice_date_due}</a></td>
                                <td><a style="font-family:Arial;">${invoice.amount_total:,.2f}</a></td>
                                <td></td>
                            </tr>
                        '''
                        property_total += invoice.amount_total
                else:
                    payment_link = f'{invoice.get_base_url()}{invoice.get_portal_url()}'
                    html_content += f'''
                        <tr>
                            <td><a style="font-family:Arial;">{invoice.name}</a></td>
                            <td><a style="font-family:Arial;">{invoice.payment_reference}</a></td>
                            <td><a style="font-family:Arial;">{invoice.invoice_date_due}</a></td>
                            <td><a style="font-family:Arial;">${invoice.amount_total:,.2f}</a></td>
                            <td colspan="4" style="text-align:center;">
                                <a href="{payment_link}" style="
                                    display: inline-block;
                                    background-color: #000000;
                                    border: 2px solid #1A1A1A;
                                    border-radius: 12px;
                                    box-sizing: border-box;
                                    color: #FFFFFF;
                                    cursor: pointer;
                                    font-family: Arial;
                                    font-size: 12px;
                                    font-weight: 600;
                                    line-height: normal;
                                    margin: 6;
                                    min-height: 40px;
                                    outline: none;
                                    padding: 12px 18px;
                                    text-align: center;
                                    text-decoration: none;
                                    transition: all 300ms cubic-bezier(.23, 1, 0.32, 1);
                                    user-select: none;
                                    width: 80%;
                                    -webkit-user-select: none;
                                    touch-action: manipulation;
                                    will-change: transform;
                                "><strong>PAY NOW</strong></a>
                            </td>
                        </tr>
                    '''
                    property_total += invoice.amount_total
            html_content += f'''
                    <tr>
                        <td colspan="3"><strong style="font-family:Arial;">PROPERTY TOTAL</strong></td>
                        <td><strong style="font-family:Arial;">${property_total:,.2f}</strong></td>
                    </tr>
                </table>
            '''
            overall_total += property_total

            html_content += f'<h3 style="font-family:Arial;">Overall Total: ${overall_total:,.2f}</h3>'

            #email_addresses = [customer.email] if customer.email else []
            email_addresses = []
            #email_addresses.extend([child.email for child in customer.child_ids if child.email])
            email_addresses.extend(["diego@adanordonezp.com", "management@adanordonezp.com", "zanggely@adanordonezp.com", "alejandro@adanordonezp.com", "celeste@adanordonezp.com", "support@adanordonezp.com", "cfl@adanordonezp.com"])
            # email_addresses lista 

            email_to = ','.join(email_addresses)

            if email_to:
                mail_values = {
                    'subject': f'Hold en Proyectos de Construcción por Pagos Pendientes',
                    'body_html': html_content,
                    'email_to': email_to,
                }
                record.env['mail.mail'].create(mail_values).send()
                record.mail_sent = True

class OnHoldWizard(models.Model):
    _name = "on.hold.wizard"
    _description = "Wizard for On Hold Properties"

    date = fields.Date(string="Date", default=fields.Date.today(), required=True)
    responsible = fields.Many2one("hr.employee", string="Responsible")
    mail_notification = fields.Boolean(string="Mail Notification")
    previous_status = fields.Selection(selection=[
        ("pending", "Pending"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("epp", "EPP"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("ppa", "PPA"),
        ("cop", "COP"),
        ("cop1", "COP1"),
        ("cop2", "COP2"),
        ("cop3", "COP3"),
        ("cop4", "COP4"),
        ("coc", "COC"),
        ("completed", "Completed"),
        ], string="Construction Status",
        readonly=False, copy=False, index=True,
        default='') # unkown parameter tracking=True
    comments = fields.Text(string="Comments")
    jennys_calls = fields.Text(string="Jenny's Calls")
    hold_by_owner = fields.Boolean(string="Hold by Owner", default=False, help="Indicates if the property is on hold by the owner.")

    def save_history(self):
        property_name = self._context.get('default_property_id')
        property = self.env['pms.property'].browse(property_name)

        property.on_hold = True
        property.hold_by_owner = self.hold_by_owner
        property.date_last_set_on_hold = self.date
        
        if property.analytical_account:
            analytic_lines = self.env['account.analytic.line'].search([
                ('account_id', '=', property.analytical_account.id)
            ])
            
        processed_moves = set()

        for analytic_line in analytic_lines:
            if analytic_line.move_line_id:
                move_line = analytic_line.move_line_id
                if move_line.move_id:
                    move = move_line.move_id
                    if move and move.id not in processed_moves:
                        note = f'''
                            <div style="background-color: #D6EBF0; color: #000000; padding: 10px; margin-right: 15px; margin-top: 10px; border-radius: 10px; border: 1px solid #AED9E1">
                                <b>{property.name} has been put on hold</b><br>
                                <i>Reason: {self.comments}</i>
                            </div>
                        '''
                        move.message_post(body=note)
                        processed_moves.add(move.id)

        on_hold_data = {
            "property_name": property_name,
            "date": self.date,
            "responsible": self.responsible.id,
            "mail_notification": self.mail_notification,
            "previous_status": self.previous_status,
            "comments": self.comments,
            "jennys_calls": self.jennys_calls,
        }

        self.env["pms.on.hold.history"].create(on_hold_data)

        property.on_hold_comments()


class OffHoldWizard(models.Model):
    _name = "off.hold.wizard"
    _description = "Wizard for Off Hold Properties"

    off_hold_reason = fields.Text(string="Off Hold Reason")

    def save_history(self):
        property_name = self._context.get('default_property_id')
        history = self.env['pms.on.hold.history'].search([('property_name', '=', property_name), ('hold_end_date', '=', False)], order='date desc')

        for record in  history:
            record.write({
                "off_hold_reason": self.off_hold_reason,
                "hold_end_date": datetime.now(),
            })
