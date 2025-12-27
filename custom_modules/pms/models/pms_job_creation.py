from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PmsJobCreation(models.Model):
    _name = 'pms.job.creation'
    _description = 'Job Creation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
    _rec_name = 'display_name'

    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    name = fields.Many2one('pms.job.product', required=True, string='Job Name')
    project_activity = fields.Many2one('pms.projects.routes.templates.lines', string='Project Activity') # duplicate string
    activity_created = fields.Boolean(string='Activity Created', default=False)
    activity_id  = fields.Many2one('pms.projects.routes', string='Activity ID') # duplicate string
    description = fields.Text(string='Description')
    due_date = fields.Date(string='Due Date')
    completed_date = fields.Date(string='Completed Date')
    priotity = fields.Selection([('urgent', 'Urgent'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], string='Priority', default='medium')
    assigned_to = fields.Many2many('hr.employee', 'job_creation_assigned_to', 'job_creation_id', 'assigned_to', string='Assigned To')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='draft', readonly=True, tracking=True)
    address = fields.Many2one('pms.property', string='Address')
    photo = fields.Many2many('ir.attachment', string='Photo')
    county = fields.Many2one(related="address.county", string='County', store=True)
    superintendent = fields.Many2one(related="address.superintendent", string='Superintendent', store=True)
    contractor = fields.Many2one("res.partner", string="Contractor", store=True)
    amount = fields.Float(string='Amount')
    invoiced = fields.Boolean(string='Invoiced', readonly=True)
    collected = fields.Boolean(string='Collected', readonly=True, compute='_compute_collected')
    invoice_id = fields.Integer(string='Invoice')
    company_invoice = fields.Many2one('res.company', string='Company Invoice')

    def _compute_collected(self):
        for record in self:
            if record.invoice_id:
                bill = self.env['account.move'].sudo().browse(record.invoice_id)
                if bill.payment_state == 'paid' or bill.payment_state == 'in_payment':
                    record.collected = True
                else:
                    record.collected = False
            else:
                record.collected = False

    def create_project_activity(self):
        for record in self:
            
            if record.activity_created:
                raise ValidationError('Activity already created')
            elif record.project_activity.id == False:
                raise ValidationError('Please select an activity')
            elif record.address.id == False:
                raise ValidationError('Please select an address')
            else:
                pms_project = self.env['pms.projects'].search([('address', '=', record.address.id)])
                if pms_project:
                    activity = self.env['pms.projects.routes'].create({
                        'project_property': pms_project.id,
                        'name': record.project_activity.id,
                        'vendor': record.contractor.id if record.contractor else False,
                        'comments': record.description,
                        'start_date': record.create_date,
                        'order_date': record.create_date,
                        'end_date': record.completed_date,
                        'expected_end_date': record.due_date,
                        'completed': True if record.status == 'completed' else False,
                    })
                    record.activity_id = activity
                    record.activity_created = True
                else:
                    raise ValidationError(f'Project not found')

    @api.depends('name', 'address')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.name.job_name} - {rec.address.name}'

    def set_in_progress(self):
        self.status = 'in_progress'

    def set_completed(self):
        self.status = 'completed'
        if self.activity_id:
            self.activity_id.completed = True
            self.activity_id.end_date = self.completed_date

    def set_draft(self):
        self.status = 'draft'
    
    def view_invoice(self):
        return {
            'name': 'Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
    
    def open_invoice_creation(self):
        return {
            'name': 'Create Invoice',
            'view_mode': 'form',
            'res_model': 'company.selection.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }

    def create_invoice(self):
        invoice = self.env['account.move'].create({
            'partner_id': self.address.partner_id.id,
            'company_id': self.company_invoice.id,
            'move_type': 'out_invoice',
            'contractor': self.contractor.id if self.contractor else False,
            'payment_reference': self.description,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': self.name.job_name,
                'quantity': 1,
                'price_unit': self.amount,
            })]
        })
        self.invoiced = True
        self.invoice_id = invoice.id

        for attachment in self.photo:
            attachment.copy({'res_id': invoice.id, 'res_model': 'account.move'}) 
            
        return {
            'name': 'Invoice',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

class PmsJobProduct(models.Model):
    _name = 'pms.job.product'
    _description = 'Job Product'
    _rec_name = 'job_name'

    job_name = fields.Char(string='Job Name', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    pms_job_creation_ids = fields.Many2many('pms.job.creation', string='Job Creations')

class CompanySelectorWizard(models.TransientModel):
    _name = 'company.selection.wizard'
    _description = 'Company Selector Wizard'

    company = fields.Many2one('res.company', string='Company', required=True)

    def confirm_selection(self):
        record_id = self._context.get('active_id')
        job_record = self.env['pms.job.creation'].browse(record_id)
        job_record.company_invoice = self.company.id
        job_record.create_invoice()
        inv_id = job_record.invoice_id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice', 
            'res_model': 'account.move',
            'res_id': inv_id,
            'view_mode': 'form',
            'target': 'current',
        }