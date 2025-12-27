from odoo import api, fields, models, Command
from odoo.exceptions import ValidationError, UserError


class autobill_1stwizard(models.TransientModel):
    _name = "autobill.1stwizard"
    _description = "auto bill 1st wizard"

    date = fields.Date(string="Date", required=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor", required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    reference = fields.Char(string='Reference')
    invoice_number = fields.Char(string='Invoice Number')
    payment_link = fields.Char(string='Payment Link')

    def next(self):
        rules = self.env['accounting.rules'].search([('vendor', '=', self.vendor_id.id)])
        if len(rules.ids) > 0:
            second_wizard = self.env.ref('accounting_wizard.view_auto_bill_2ndwizard_form')
            attachments_ids = self.attachment_ids.ids
            return {
                'name': 'view_auto_bill_2ndwizard_form',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'autobill.2ndwizard',
                'views': [(second_wizard.id, 'form')],
                'view_id': second_wizard.id,
                'target': 'new',
                'context': {
                    'vendor': self.vendor_id.id,
                    'default_attachment_ids': attachments_ids,
                    'date': self.date,
                    'reference': self.reference,
                    'invoice_number': self.invoice_number,
                    'payment_link': self.payment_link
                }
            }
        else:
            raise UserError('No rules found for this vendor')

class autobill_2ndwizard(models.TransientModel):
    _name = "autobill.2ndwizard"
    _description = "auto bill 2nd wizard"

    second_wizard_data = fields.One2many('autobill.2ndwizard.line', 'second_wizard', string='Second Wizard Data')

    duplicate_alert = fields.Char(string='Duplicate Alert', readonly=True)
    price_alert = fields.Char(string='Price Alert', readonly=True)
    servicio_alert = fields.Char(string='Servicio Facturado Alert', readonly=True)
    
    def confirm(self):
        dup_list = []
        price_budget_list = []
        pre_invoiced_list = []

#---------------------------------------------------------------------------------------------------------- 
        for line in self.second_wizard_data:
            # first validations
            
            if line.product_type == 'material':
                if line.subproduct.id ==  False:
                    raise UserError('Subproduct is requiered for materials')
        
            if line.total <= 0:
                raise UserError('Total must be greater than 0')
            
            if line.account_id.id == False:
                raise UserError('Account is required')
            
            if line.company.id == False:
                raise UserError('Company is required')
            
            if line.rule_to_apply == False:
                raise UserError('No rule found that applies for line ' + line.label)
            

#----------------------------------------------------------------------------------------------------------
        # check duplicates
            dup = self.env["account.analytic.line"].search(["&",("product_id.product_tmpl_id", "=", line.product_id.id), "&", ("account_id", "=", line.property_address.analytical_account.id), ("category", "=", "vendor_bill")])
            dup_list.extend(dup.move_line_id.mapped("move_id.id"))
#----------------------------------------------------------------------------------------------------------
            # check budget
            if line.property_address:
                budget = self.env['budget.model'].search(["&", ('product_model', '=', line.product_id.id), ('house_model', '=', line.property_address.house_model.id)])
                if len(budget.ids) > 0:
                    budget_total_now = self.env["account.analytic.line"].search(["&",("product_id.product_tmpl_id", "=", line.product_id.id), "&", ("account_id", "=", line.property_address.analytical_account.id), ("category", "=", "vendor_bill")]).ids
                    if len(budget_total_now) > 1:
                        budget_total_now = sum(self.env["account.analytic.line"].browse(budget_total_now).mapped("amount"))
                    elif len(budget_total_now) == 1:
                        budget_total_now = self.env["account.analytic.line"].browse(budget_total_now).amount
                    else:
                        budget_total_now = 0

                    new_total = -budget_total_now + line.total
                    
                    if new_total > budget.amount:
                        price_budget_list.append(line.product_id.name)
#----------------------------------------------------------------------------------------------------------

            # check servicio facturado

                pre_invoiced_result = self.env['accounting.rules'].browse(line.rule_to_apply).pre_invoiced
                if pre_invoiced_result:
                    pre_invoiced = self.env["account.analytic.line"].search(["&",("product_id.product_tmpl_id", "=", line.product_id.id), "&", ("account_id", "=", line.property_address.analytical_account.id), ("category", "=", "")])
                    if len(pre_invoiced) > 1:
                        pre_invoiced = sum(self.env["account.analytic.line"].browse(pre_invoiced).mapped("amount"))
                    elif len(pre_invoiced) == 1:
                        pre_invoiced = self.env["account.analytic.line"].browse(pre_invoiced).amount
                    else:
                        pre_invoiced = 0

                    if line.total > pre_invoiced:
                        pre_invoiced_list.append(line.product_id.name)
                        
                    
    
#----------------------------------------------------------------------------------------------------------
            # duplicates alert
        if len(dup_list) > 0:
            self.duplicate_alert = f'There are similar bills in the system'
        else:
            self.duplicate_alert = "No duplicates found"

#----------------------------------------------------------------------------------------------------------
        # budget alert
        if len(price_budget_list) > 0:
            price_budget_list = ",".join(str(element) for element in price_budget_list)
            self.price_alert = f'The following products exceed the budget please inform before proceeding {price_budget_list}'
        else:
            self.price_alert = "No budget exceed"
#----------------------------------------------------------------------------------------------------------
        
        # check servicio facturado
        if len(pre_invoiced_list) > 0:
            pre_invoiced_list = ",".join(str(element) for element in pre_invoiced_list)
            self.servicio_alert = f'The following products have been invoiced with a lower amount than this bill: {pre_invoiced_list}'
        else:
            self.servicio_alert = "No more Alerts here"

#----------------------------------------------------------------------------------------------------------
        move_data = []
        responsibles = []
        for line in self.second_wizard_data:
            rule_to_use = self.env['accounting.rules'].browse(line.rule_to_apply)
            responsibles.append(rule_to_use.responsible_to_pay.id)
            move_data.append({
                'property_address': line.property_address.id,
                'company': line.company.id,
                'product_type': line.product_type,
                'subproduct': line.subproduct.id,
                'product_id': line.product_id.id,
                'account_id': line.account_id.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'total': line.total,
                'label': line.label,
                'rule_to_apply': line.rule_to_apply
            })

        responsibles = list(dict.fromkeys(responsibles))
        return {'type': 'ir.actions.act_window',
                'name': 'Confirmation Wizard',
                'res_model': 'auto.duplicate.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('accounting_wizard.view_auto_duplicate_bill_wizard_form').id,
                'target': 'new',
                'context': {
                            'bill_ids': dup_list,
                            'move_data': move_data,
                            'companies': self.second_wizard_data.mapped('company.id'),
                            'responsibles': responsibles,
                            'user_id': self.env.user.id,
                            'price_mssg': self.price_alert,
                            'duplicate_mssg': self.duplicate_alert,
                            'preinvoice_mssg': self.servicio_alert,
                            'vendor': self._context.get('vendor'),
                            'default_attachment_ids': self._context.get('default_attachment_ids'),
                            'date': self._context.get('date'),
                            'reference': self._context.get('reference'),
                            'invoice_number': self._context.get('invoice_number'),
                            'payment_link': self._context.get('payment_link')
                            }}
        

class autobill_2ndwizard_line(models.TransientModel):
    _name = "autobill.2ndwizard.line"
    _description = "auto bill 2nd wizard line"

    #second wizard
    property_address = fields.Many2one('pms.property', string='Property Address')
    company = fields.Many2one('res.company', string='Company')
    product_type = fields.Selection([('material', 'Material'), ('labor', 'Labor')], string='Product Type', required=True, default='labor')
    subproduct = fields.Many2one('product.subproduct', string='Subproduct')
    product_id = fields.Many2one('product.template', string='Product')
    account_id = fields.Many2one('account.account', string='Account', required=True, readonly=False, compute='_account_calculate')
    quantity = fields.Float(string='Quantity', required=True, default=1)
    price_unit = fields.Float(string='Price Unit', required=True, default=0)
    total = fields.Float(string='Total', compute='_compute_total', readonly=True)
    label = fields.Char(string='Label')
    allowed_products = fields.Many2many('product.template', string='Allowed Products')
    rule_to_apply = fields.Integer(string='Rule to Apply', required=True)

    second_wizard = fields.Many2one('autobill.2ndwizard', string='Second Wizard')

    @api.depends('product_id', 'company')
    def _account_calculate(self):
        for record in self:
            if record.product_id and record.company:
                record.account_id = record.with_company(record.company.id).product_id.categ_id.property_account_expense_categ_id.id

    def _apply_rules(self, vendor):
        company_id = False
        if self.property_address:
            property_owner = self.property_address.partner_id
            company_id = self.env['res.company'].search([('partner_id', '=', property_owner.id)]).id
            project = self.env['pms.projects'].search([('address', '=', self.property_address.id)])
            if company_id:
                property_type = 'own'
            elif project.on_off_hold:
                property_type = 'on_hold'
            elif project.custodial_money:
                property_type = 'escrow'
                company_id = project.escrow_company.id
            else:
                property_type = 'third'

            county = self.property_address.county
            status = self.property_address.status_property
            
            if status != 'construction' and  status != 'rented':
                status = 'construction'

            rules = self.env['accounting.rules'].search(["&", ('vendor', '=', vendor), '&', '|', ('applies_to', '=', property_type), ('applies_to', '=', 'all'), '&', '|', ('county', '=', county.id), ('county', '=', False), '&', '|', ('house_status', '=', status), ('house_status', '=', False), '|', ('material_labor', '=', self.product_type), ('material_labor', '=', False)])
            
            if self.product_id:
                rules = rules.filtered(lambda r: self.product_id in r.allowed_products)
            
            rules = rules.sorted(key=lambda r: r.sequence)
            
            if rules[0].if_own_go_to_owner == False and property_type == 'own':
                company_id = rules[0].company.id
            
            if rules[0].if_escrow_go_to_owner == False and property_type == 'escrow':
                company_id = rules[0].company.id

        else:
            rules = self.env['accounting.rules'].search(["&", ('vendor', '=', vendor), '|', ('material_labor', '=', self.product_type), ('material_labor', '=', False)])
            
            if self.product_id:
                rules = rules.filtered(lambda r: self.product_id in r.allowed_products)
            
            
            rules = rules.sorted(key=lambda r: r.sequence)
            # put allowed products and accounts
        
        if rules:
            if company_id == False:
                company_id = rules[0].company.id

            if rules[0].account_to_auto_complete:
                account_to_auto_complete = rules[0].account_to_auto_complete.id
            else:
                account_to_auto_complete = False

            return rules, company_id, account_to_auto_complete
        else:
            return False, False
            


    @api.constrains('quantity', 'price_unit')
    def _check_quantity_price_unit(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError('Quantity must be greater than 0')
            if record.price_unit <= 0:
                raise ValidationError('Price Unit must be greater than 0')
            
    @api.onchange('product_id')
    def _onchange_product_id(self):
        vendor = self._context.get('vendor')
        if self.product_id:
            
            rules, company, account_to_auto_complete = self._apply_rules(vendor)

            if rules == False:
                self.company = False
            else:
                self.company = company
                self.allowed_products = rules.allowed_products
                self.rule_to_apply = int(rules.ids[0])

            if self.company:
                self.account_id = self.with_company(self.company.id).product_id.categ_id.property_account_expense_categ_id.id
            
            if account_to_auto_complete:
                self.account_id = account_to_auto_complete
                


    @api.onchange('property_address')
    def _onchange_property_address(self):
        vendor = self._context.get('vendor')


        if self.property_address:
            rules, company, account_to_auto_complete = self._apply_rules(vendor)
            if rules == False:
                self.company = False
            else:
                self.company = company
                self.allowed_products = rules.allowed_products
                self.rule_to_apply = int(rules.ids[0])
            
            if account_to_auto_complete:
                self.account_id = account_to_auto_complete


            # allowed products and accounts
    
    @api.onchange('product_type')
    def _onchange_product_type(self):
        if self.product_type:
            vendor = self._context.get('vendor')
            if self.product_type == 'labor':
                rules, company, account_to_auto_complete = self._apply_rules(vendor)
                if rules == False:
                    self.company = False
                else:
                    self.company = company
                    self.allowed_products = rules.allowed_products
                    self.rule_to_apply = int(rules.ids[0])

                
                if account_to_auto_complete:
                    self.account_id = account_to_auto_complete

                # allowed products and accounts
            else:
                self.subproduct = False
                rules, company, account_to_auto_complete = self._apply_rules(vendor)
                if rules == False:
                    self.company = False
                else:
                    self.company = company
                    self.allowed_products = rules.allowed_products
                    self.rule_to_apply = int(rules.ids[0])

                if account_to_auto_complete:
                    self.account_id = account_to_auto_complete


                # allowed products and accounts

    @api.depends('quantity', 'price_unit')
    def _compute_total(self):
        for record in self:
            record.total = record.quantity * record.price_unit
        


class auto_bill_duplicate_wizard(models.TransientModel):
    _name = 'auto.duplicate.wizard'
    _description = 'Duplicate Auto bill Wizard'

    duplicate_alert = fields.Char(default=lambda self: self.env.context.get('duplicate_mssg', False), store=False, readonly=True, string="Duplicate Alert")
    price_alert = fields.Char(default=lambda self: self.env.context.get('price_mssg', False), store=False, readonly=True, string="Price Alert")
    servicio_alert = fields.Char(default=lambda self: self.env.context.get('preinvoice_mssg', False), store=False, readonly=True, string="Pre Invoice Alert")
    bills_msg = fields.Text(default=lambda self: self.env.context.get('bill_mssg', False), store=False, readonly=True, string="Bill data")

    def post(self):
        move_data = self.env.context.get('move_data')
        companies = self.env.context.get('companies')
        move_date = self.env.context.get('date')
        invoice_number = self.env.context.get('invoice_number')
        payment_link = self.env.context.get('payment_link')
        vendor = self.env.context.get('vendor')
        reference = self.env.context.get('reference')
        attachments = self.env.context.get('default_attachment_ids')
        user_id = self.env.context.get('user_id')
        
        responsibles = self.env.context.get('responsibles')

        idx = 0
        for company_id in companies:
            for responsible in responsibles:
                idx += 1    
                if responsible == False:
                    responsible_to_use = user_id
                else:
                    responsible_to_use = responsible

                header =  {
                    'move_type': 'in_invoice',
                    'date': move_date,
                    'invoice_date': move_date,
                    'partner_id': vendor,
                    'budget_date': move_date,
                    'ref': f'{reference}, #{idx}',
                    'payment_reference': f'{reference}, #{idx}',
                    'line_ids': [],
                    'company_id': company_id,
                    'user_id': user_id,
                    'invoice_user_id': responsible_to_use,
                    }
                lines_created = False
                lines = []
                for line in move_data:
                    rule_to_use = self.env['accounting.rules'].browse(line['rule_to_apply'])
                    if line['company'] == company_id:
                        if rule_to_use.responsible_to_pay.id == responsible:
                            
                            # Separate bill into two parts if two different billables rules
                            if rule_to_use.billable:
                                if line['company'] == company_id:
                                    if rule_to_use.responsible_to_pay.id == responsible:
                                        line_vals = {
                                            'product_id': line['product_id'],
                                            'quantity': line['quantity'],
                                            'subproducts': line['subproduct'],
                                            'price_unit': line['price_unit'],
                                            'account_id': line['account_id'],
                                            'name': line['label'],
                                            'analytic_distribution': {str(self.env['pms.property'].browse(line['property_address']).analytical_account.id): 100.0},
                                            'billable': True,
                                            'markup': rule_to_use.markup,
                                        }
                                        
                                        lines.append(Command.create(line_vals))
                                        lines_created = True
                            # Add custom rules created by user in select
                            elif rule_to_use.classify_folder:

                                attachment_folder = rule_to_use.folder
                                attachment_data = {
                                    'attachment_id': attachments[0],
                                    'partner_id': vendor,
                                    'owner_id': responsible_to_use,
                                    'folder_id': attachment_folder.id,
                                    'concept': line['label'],
                                    'date': move_date,
                                    'amount': line['total'],
                                    'invoice_number': invoice_number,
                                }
                                attachment_record = self.env['documents.document'].create(attachment_data)

                                attachment_record.message_post(body=payment_link)

                            else:
                                line_vals = {
                                    'product_id': line['product_id'],
                                    'quantity': line['quantity'],
                                    'subproducts': line['subproduct'],
                                    'price_unit': line['price_unit'],
                                    'account_id': line['account_id'],
                                    'analytic_distribution': {str(self.env['pms.property'].browse(line['property_address']).analytical_account.id): 100.0},
                                    'name': line['label'],
                                }
                                
                                lines.append(Command.create(line_vals))
                                lines_created = True

                if lines_created:
                    # missing checking company, user above and returning to show bill or list of bills
                    header['line_ids'] += lines
                    bill_created = self.env['account.move'].with_company(company_id).create(header)
                    bill_created.action_post()
                    bill_created.message_post(body=f'Bill created from {reference} with number {invoice_number} and payment link {payment_link}, by user {self.env.user.name} in accounting wizard')
                    attachment_loaning = self.env["ir.attachment"]
                    for attachment_id in attachments:
                        attachment_loaning = attachment_loaning.browse(attachment_id)
                        attachment_loaning.copy({'res_id': bill_created.id, 'res_model': 'account.move'})
                

    def cancel_bill(self):
        return {'type': 'ir.actions.act_window_close'}

    def view_similar_bills(self):
        ctx = self.env.context.get('bill_ids')
        return {
            'type': 'ir.actions.act_window',
            'name': ('view_invoice_tree'),
            'res_model': 'account.move',
            'view_mode': 'tree',
            'domain': [('id', 'in', ctx)]
        }