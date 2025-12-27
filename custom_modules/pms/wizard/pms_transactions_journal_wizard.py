from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.fields import Command

class pms_transaction_journal_wizard(models.TransientModel):
    _name = 'pms.transaction.journal.wizard'
    _description = 'Transaction Journal Wizard'

    # Get data from the transaction
    transaction_id = fields.Many2one("pms.transactions", string="Transaction", required=True)
    transaction_type = fields.Selection(related="transaction_id.transaction_type", string="Transaction Type")
    owner = fields.Many2one(related="transaction_id.owner", string="New Owner")
    old_owner = fields.Many2one(related="transaction_id.old_owner", string="Old Owner")
    property_address = fields.Many2one(related="transaction_id.property_address", string="Property Address")
    residential_unit_closure = fields.Boolean(related="transaction_id.property_address.residential_unit_closure", string="Residential Unit Closure")
    type_purchase_sale = fields.Selection([('land', 'Land'), ('construction', 'Finished Construction')], string="Type of Purchase/Sale")

    # Key Numbers
    net_closing_cost = fields.Float(string="Closing Cost", required=True) # Se muestra en todas las transacciones
    escrow_money = fields.Float(string="Escrow Money") # Se muestra en todas las transacciones
    amount_to_pay = fields.Float(string="Amount to Pay") # Se muestra en todas las transacciones
    amount_to_receive = fields.Float(string="Amount to Receive") # Se muestra en todas las transacciones

    # SALES & REFINANCE NUMBER
    sales_price = fields.Float(string="Sales Price") # Se muestra en las ventas, es requerido en ventas
    item_details = fields.Boolean(string="Check Construction Report so no items are left behind and it checks with gl amount", default=False) # Se requiere true en vetnas y refinanciamientos
    property_cost = fields.Float(string="Property Cost") # Se muestra en las ventas y refinanciamientos, es requerido en ventas y refinanciamientos

    # LOAN DETAILS (SOLO SE MUESTRA EN VENTAS Y REFINANCIAMIENTOS)
    has_previous_loan = fields.Boolean(string="Has Previous Loan") # Se muestra en las ventas y refinanciamientos, es requerido como true en refinanciamientos
    previous_loan_amount = fields.Float(string="Previous Loan Amount") # Se muestra en las ventas y refinanciamientos, es requerido como true en refinanciamientos
    previous_loan_interest = fields.Float(string="Previous Loan Interest") # Se muestra en las ventas y refinanciamientos, es requerido como true en refinanciamientos
    previous_loan_secure_investment = fields.Float(string="Previous Loan Drawed amount if applicable") # Se muestra en las ventas y refinanciamientos
    previous_loan_amount_match = fields.Boolean(string="Previous Loan Amount Matches with other company?") # Se muestra en las refinanciamientos solo se requiere alli

    mortgage_cost_refinance = fields.Float(string="Mortgage Cost Refinance") # Se muestra en las refinanciamientos
    escrow_money_refinance = fields.Float(string="Escrow Money Refinance") # Se muestra en las refinanciamientos
    insurance_refinance = fields.Float(string="Insurance Refinance") # Se muestra en las refinanciamientos
    taxes_refinance = fields.Float(string="Property Taxes Refinance") # Se muestra en las refinanciamientos

    new_loan_amount = fields.Float(string="New Loan Amount") # Se muestra en las refinanciamientos, se requiere en refi

    # PURCHASE NUMBERS
    price_of_land = fields.Float(string="Price of Land") # Se muestra en las compras, es requerido en compras

    warranty_deed = fields.Many2many('ir.attachment', string='Warranty Deed', relation='wizard_warranty_deed_rel')  # Se muestras las ventas y compras
    hud_attachment = fields.Many2many('ir.attachment', string='HUD Attachment', required=True, relation='wizard_hud_attachment_rel') # Se muestra en las ventas y compras, es requerido en ventas y compras
    payoff_details = fields.Many2many('ir.attachment', string='Payoff Details', relation='wizard_payoff_details_rel') # Refinanciamientos, se muestra en los demas
    lender_package = fields.Many2many('ir.attachment', string='Lender Package', relation='wizard_lender_package_rel') # Refinanciamientos y solo se muestra alli

    note = fields.Text(string="Note") # Siempre y que se ponga en el mensaje de los asientos

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
    def create_closing(self):
        new_owner = self._context.get('default_owner')
        old_owner = self._context.get('default_old_owner')
        # TODAS LINEAS CON ANALYTIC
        # EN caso de compra
        # 1 solo asiento en el new owner
        # los clips y mensajes llenos
        # DEBIT: price_of_land con producto land purchase price = '1000201' & net_closing_cost con producto: land closing cost = '1000201', CREDIT: escrow_money, amount_to_pay
        company_new = self.env["res.company"].search([("partner_id", "=", new_owner)])
        company_old = self.env["res.company"].search([("partner_id", "=", old_owner)])
        if self.transaction_type == 'purchase':
            if not self.price_of_land:
                raise ValidationError("Please fill the price of land")
            if not self.hud_attachment:
                raise ValidationError("Please attach the HUD Attachment")
                     
            purchase_entry_lines = []

            purchase_entry = {
                'move_type': 'entry',
                'date': self.transaction_id.transaction_date,
                'budget_date': self.transaction_id.transaction_date,
                'company_id': company_new.id,
                'ref': self.transaction_id.name,
                'line_ids': [],
            }

            account_code = ""
            if self.residential_unit_closure == True:
                account_code = "1000202"
            else:   
                account_code = "1000201"

            product_land_purchase_price = self.env["product.template"].search(["&", ("company_id", "=", company_new.id), ("name", "ilike", "Land Purchase Price")]).product_variant_id.id
            product_land_closing_cost = self.env["product.template"].search(["&", ("company_id", "=", company_new.id), ("name", "ilike", "Land Closing Costs")]).product_variant_id.id

            debit_lines_price_of_land = {
                'product_id': self.env["product.product"].search([("id", "=", product_land_purchase_price)]).id,
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                'name': 'Price of Land',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.price_of_land, 2),
                'credit': 0.0,
            }

            debit_lines_net_closing_cost = {
                'product_id': self.env["product.product"].search([("id", "=", product_land_closing_cost)]).id,
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                'name': 'Land Closing Cost',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.net_closing_cost, 2),
                'credit': 0.0,
            }

            credit_lines_escrow = {
                    'name': 'Escrow Money',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'account_id': self.env["account.account"].search(["&", ("code", "=", "1815202"), ("company_id", "=", company_new.id)]).id,
                    'debit': 0.0,
                    'credit': round(self.escrow_money, 2),
            }

            credit_lines_amount_to_pay = {
                    'name': 'Amount to Pay',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                    'debit': 0.0,
                    'credit': round(self.amount_to_pay, 2),
            }

            purchase_entry_lines.append(Command.create(credit_lines_escrow))
            purchase_entry_lines.append(Command.create(credit_lines_amount_to_pay))
            purchase_entry_lines.append(Command.create(debit_lines_price_of_land))
            purchase_entry_lines.append(Command.create(debit_lines_net_closing_cost))

            purchase_entry['line_ids'] += purchase_entry_lines

            journal_transaction_purchase = self.env['account.move'].sudo().create(purchase_entry)
            journal_transaction_purchase.action_post()
            if self.note:
                journal_transaction_purchase.message_post(body=self.note)
            attachment_model = self.env["ir.attachment"]
            if self.warranty_deed:
                attachment_warranty_deed = attachment_model.browse(self.warranty_deed.ids)
                attachment_warranty_deed.copy({'res_id': journal_transaction_purchase.id, 'res_model': 'account.move'})
            attachment_hud_attachment = attachment_model.browse(self.hud_attachment.ids)
            attachment_hud_attachment.copy({'res_id': journal_transaction_purchase.id, 'res_model': 'account.move'})
            if self.payoff_details:
                attachment_payoff_details = attachment_model.browse(self.payoff_details.ids)
                attachment_payoff_details.copy({'res_id': journal_transaction_purchase.id, 'res_model': 'account.move'})
            
            action = {

                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': journal_transaction_purchase.id,
                'target': 'current',
            }

            return action

        # EN caso de venta
        # 1 solo asiento en el old owner
        # los clips y mensajes llenos
        # DEBIT: escrow_money, amount_to_receive,  CREDIT: sales price, net_closing_cost (depende si es positivo/debito o negativo/credito)
        # DEBIT: property_cost = 'cuenta de costo', CREDIT: property_cost = '1000201' o '1000202' si es residencial
        # IF BOOLEAN HAS PREVIOUS LOAN = TRUE
        # DEBIT: previous_loan_amount, previous_loan_interest CREDIT: previous_loan_secure_investment

        if self.transaction_type == 'sale':
            if not self.sales_price:
                raise ValidationError("Please fill the sales price")
            if not self.hud_attachment:
                raise ValidationError("Please attach the HUD Attachment")
            if self.item_details == False:
                raise ValidationError("Please check the item details")
            if not self.property_cost:
                raise ValidationError("Please fill the property cost")
            
            sale_entry_lines = []

            sale_entry = {
                'move_type': 'entry',
                'date': self.transaction_id.transaction_date,
                'budget_date': self.transaction_id.transaction_date,
                'company_id': company_old.id,
                'ref': self.transaction_id.name,
                'line_ids': [],
            }

            account_code = ""
            if self.residential_unit_closure == True:
                account_code = "1000202"
            else:   
                account_code = "1000201"

            if self.has_previous_loan == True:
                if not self.previous_loan_amount:
                    raise ValidationError("Please fill the previous loan amount")
                
                debit_lines_previous_loan_amount = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", "2000402"), ("company_id", "=", company_old.id)]).id,
                    'name': 'Previous Loan Amount',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit': round(self.previous_loan_amount, 2),
                    'credit': 0.0,
                }

                debit_lines_previous_loan_interest = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_old.id)]).id,
                    'name': 'Previous Loan Interest',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit': round(self.previous_loan_interest, 2),
                    'credit': 0.0,
                }

                credit_lines_previous_loan_secure_investment = {
                    'name': 'Previous Loan Secure Investment',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'account_id': self.env["account.account"].search(["&", ("code", "=", "1000206"), ("company_id", "=", company_old.id)]).id,
                    'debit': 0.0,
                    'credit': round(self.previous_loan_secure_investment, 2),
            }


            debit_lines_escrow_money = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "1815202"), ("company_id", "=", company_old.id)]).id,
                'name': 'Escrow Money',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.escrow_money, 2),
                'credit': 0.0,
            }

            debit_lines_amount_to_receive = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_old.id)]).id,
                'name': 'Amount to Receive',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.amount_to_receive, 2),
                'credit': 0.0,
            }

            debit_lines_property_costs = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "5100000"), ("company_id", "=", company_old.id)]).id,
                'name': 'Property Cost',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.property_cost, 2),
                'credit': 0.0,
            }

            credit_lines_sales_price = {
                    'name': 'Sales Price',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'account_id': self.env["account.account"].search(["&", ("code", "=", "4000002"), ("company_id", "=", company_old.id)]).id,
                    'debit': 0.0,
                    'credit': round(self.sales_price, 2),
            }

            if self.net_closing_cost > 0:

                debit_lines_net_closing_costs = {
                        'name': 'Net Closing Cost',
                        'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                        'account_id': self.env["account.account"].search(["&", ("code", "=", "6000028"), ("company_id", "=", company_old.id)]).id,
                        'debit': round(self.net_closing_cost, 2),
                        'credit': 0.0
                }
            
            elif self.net_closing_cost < 0:
                    
                credit_lines_net_closing_costs = {
                        'name': 'Net Closing Cost',
                        'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                        'account_id': self.env["account.account"].search(["&", ("code", "=", "6000028"), ("company_id", "=", company_old.id)]).id,
                        'debit': 0.0,
                        'credit': round(self.net_closing_cost, 2),
                }

            if self.residential_unit_closure == True:

                credit_lines_property_costs = {
                        'name': 'Property Cost',
                        'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                        'account_id': self.env["account.account"].search(["&", ("code", "=", "1000202"), ("company_id", "=", company_old.id)]).id,
                        'debit': 0.0,
                        'credit': round(self.property_cost, 2),
                }
            else:

                credit_lines_property_costs = {
                        'name': 'Property Cost',
                        'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                        'account_id': self.env["account.account"].search(["&", ("code", "=", "1000201"), ("company_id", "=", company_old.id)]).id,
                        'debit': 0.0,
                        'credit': round(self.property_cost, 2),
                }
            if self.has_previous_loan == True:
                sale_entry_lines.append(Command.create(credit_lines_previous_loan_secure_investment))
                sale_entry_lines.append(Command.create(debit_lines_previous_loan_amount))
                sale_entry_lines.append(Command.create(debit_lines_previous_loan_interest))
            sale_entry_lines.append(Command.create(credit_lines_sales_price))
            sale_entry_lines.append(Command.create(credit_lines_property_costs))
            if self.net_closing_cost > 0:
                sale_entry_lines.append(Command.create(debit_lines_net_closing_costs))
            elif self.net_closing_cost < 0:
                sale_entry_lines.append(Command.create(credit_lines_net_closing_costs))
            
            sale_entry_lines.append(Command.create(debit_lines_escrow_money))
            sale_entry_lines.append(Command.create(debit_lines_amount_to_receive))
            sale_entry_lines.append(Command.create(debit_lines_property_costs))

            sale_entry['line_ids'] += sale_entry_lines

            journal_transaction_sale = self.env['account.move'].sudo().create(sale_entry)
            journal_transaction_sale.action_post()
            if self.note:
                journal_transaction_sale.message_post(body=self.note)
            attachment_model = self.env["ir.attachment"]
            if self.warranty_deed:
                attachment_warranty_deed = attachment_model.browse(self.warranty_deed.ids)
                attachment_warranty_deed.copy({'res_id': journal_transaction_sale.id, 'res_model': 'account.move'})
            attachment_hud_attachment = attachment_model.browse(self.hud_attachment.ids)
            attachment_hud_attachment.copy({'res_id': journal_transaction_sale.id, 'res_model': 'account.move'})
            if self.payoff_details:
                attachment_payoff_details = attachment_model.browse(self.payoff_details.ids)
                attachment_payoff_details.copy({'res_id': journal_transaction_sale.id, 'res_model': 'account.move'})

            action = {

                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': journal_transaction_sale.id,
                'target': 'current',
            }

            return action

        if self.transaction_type == 'refinance':
            if not self.payoff_details:
                raise ValidationError("Please attach the Payoff Details")
            if not self.lender_package:
                raise ValidationError("Please attach the Lender Package")
            if not self.new_loan_amount:
                raise ValidationError("Please fill the new loan amount")
            if self.has_previous_loan == False:
                raise ValidationError("Please check the has previous loan field")
            if self.previous_loan_amount <= 0:
                raise ValidationError("Please fill the previous loan amount")
            if self.previous_loan_interest <= 0:
                raise ValidationError("Please fill the previous loan interest")
            if self.previous_loan_amount_match == False:
                raise ValidationError("Please check the previous loan amount match field")
            if not self.property_cost:
                raise ValidationError("Please fill the property cost")
            if self.item_details == False:
                raise ValidationError("Please check the item details")
        
        # OLD OWNER:
        # DEBIT: loan amount, loan interest, loan items(difference) loan between related companies (new owner)
        # CREDIT: property_cost = '1000201' o '1000202' si es residencial, loan secure investment

        # ULTIMO CHECK loan between related companies deben cruzar, esto solo en refinanciamientos

            refinance_entry_lines_old_owner = []

            refinance_entry_old_owner = {
                'move_type': 'entry',
                'date': self.transaction_id.transaction_date,
                'budget_date': self.transaction_id.transaction_date,
                'company_id': company_old.id,
                'ref': self.transaction_id.name,
                'line_ids': [],
            }

            account_code = ""
            if self.residential_unit_closure == True:
                account_code = "1000202"
            else:   
                account_code = "1000201"
            
            loan_items = (self.previous_loan_amount + self.previous_loan_interest - self.previous_loan_secure_investment - self.property_cost) * -1

            debit_lines_loan_items = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "2000401"), ("company_id", "=", company_old.id)]).id,
                'name': 'Loan Items',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(loan_items, 2),
                'credit': 0.0,
            }

            debit_lines_previous_loan_amount_refinance = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "2000402"), ("company_id", "=", company_old.id)]).id,
                'name': 'Previous Loan Amount',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.previous_loan_amount, 2),
                'credit': 0.0,
            }

            debit_lines_previous_loan_interest_refinance = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_old.id)]).id,
                'name': 'Previous Loan Interest',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.previous_loan_interest, 2),
                'credit': 0.0,
            }

            credit_lines_loan_secure_investment = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", "1000206"), ("company_id", "=", company_old.id)]).id,
                    'name': 'Previous Loan Secure Investment',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit': 0.0,
                    'credit': round(self.previous_loan_secure_investment, 2),
            }

            if self.residential_unit_closure == True:

                credit_lines_property_cost_refinance = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_old.id)]).id,
                    'name': 'Property Cost',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit': 0.0,
                    'credit': round(self.property_cost, 2),
                }

            elif self.residential_unit_closure == False:
                    
                credit_lines_property_cost_refinance = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_old.id)]).id,
                    'name': 'Property Cost',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit': 0.0,
                    'credit': round(self.property_cost, 2),
                }

            refinance_entry_lines_old_owner.append(Command.create(debit_lines_loan_items))
            refinance_entry_lines_old_owner.append(Command.create(debit_lines_previous_loan_amount_refinance))
            refinance_entry_lines_old_owner.append(Command.create(debit_lines_previous_loan_interest_refinance))
            refinance_entry_lines_old_owner.append(Command.create(credit_lines_loan_secure_investment))
            refinance_entry_lines_old_owner.append(Command.create(credit_lines_property_cost_refinance))

            refinance_entry_old_owner['line_ids'] += refinance_entry_lines_old_owner

            journal_transaction_refinance_old_owner = self.env['account.move'].create(refinance_entry_old_owner)
            journal_transaction_refinance_old_owner.action_post()
            if self.note:
                journal_transaction_refinance_old_owner.message_post(body=self.note)
            attachment_model = self.env["ir.attachment"]

            attachment_payoff_details = attachment_model.browse(self.payoff_details.ids)
            attachment_payoff_details.copy({'res_id': journal_transaction_refinance_old_owner.id, 'res_model': 'account.move'})
            attachment_lender_package = attachment_model.browse(self.lender_package.ids)
            attachment_lender_package.copy({'res_id': journal_transaction_refinance_old_owner.id, 'res_model': 'account.move'})
            # attachment_hud_attachment = attachment_model.browse(self.hud_attachment.ids)
            # attachment_hud_attachment.copy({'res_id': journal_transaction_refinance_old_owner.id, 'res_model': 'account.move'})


######################################################################################################################################
        # NEW OWNER:
        # DEBIT: property_cost = '1000201' o '1000202' si es residencial, amount_to_receive, mortgage_cost_refinance and other _refinance, net_closing_cost (depende si es positivo/debito o negativo/credito), 
        # DEBIT: suma previous loan amount y previous loan interest y previous loan secure investment como loan between related companies (partner old owner )
        # CREDIT: property cost = loan between related company (partner old owner), new_loan_amount, amount_to_pay
            refinance_entry_lines_new_owner = []

            refinance_entry_new_owner = {
                'move_type': 'entry',
                'date': self.transaction_id.transaction_date,
                'budget_date': self.transaction_id.transaction_date,
                'company_id': company_new.id,
                'ref': self.transaction_id.name,
                'line_ids': [],
            }

            debit_lines_amount_to_receive_new_owner = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                'name': 'Amount To Receive',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.amount_to_receive, 2),
                'credit': 0.0,
            }

            debit_lines_mortgage_cost_refinance = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                'name': 'Mortgage Cost Refinance',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.mortgage_cost_refinance, 2),
                'credit': 0.0,
            }

            debit_lines_escrow_money_refinance = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "1815202"), ("company_id", "=", company_new.id)]).id,
                'name': 'Escrow Money Refinance',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.escrow_money_refinance, 2),
                'credit': 0.0,
            }

            debit_lines_insurance_refinance = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "6000012"), ("company_id", "=", company_new.id)]).id,
                'name': 'Insurance Refinance',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.insurance_refinance, 2),
                'credit': 0.0,
            }

            debit_lines_taxes_refinance = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "6000023"), ("company_id", "=", company_new.id)]).id,
                'name': 'Taxes Refinance',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(self.taxes_refinance, 2),
                'credit': 0.0,
            }

            # debit_lines_sum_loans = {
            #     'account_id': self.env["account.account"].search(["&", ("code", "=", "2000401"), ("company_id", "=", company_new.id)]).id,
            #     'name': 'Loan Items',
            #     'partner_id': self.old_owner.id,
            #     'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
            #     'debit': round(sum_loans, 2),
            #     'credit': 0.0,
            # }

            sum_loans = self.previous_loan_amount + self.previous_loan_interest + self.previous_loan_secure_investment
            debit_lines_loan_financial_institution = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "2000402"), ("company_id", "=", company_new.id)]).id,
                'name': 'Old Loan Items',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': round(sum_loans, 2),
                'credit': 0.0,
            }

            if self.residential_unit_closure == True:

                debit_lines_property_cost_refinance = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", "1000202"), ("company_id", "=", company_new.id)]).id,
                    'name': 'Property Cost',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit':  round(self.property_cost, 2),
                    'credit':0.0,
                }

            elif self.residential_unit_closure == False:
                    
                debit_lines_property_cost_refinance = {
                    'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                    'name': 'Property Cost',
                    'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                    'debit': round(self.property_cost, 2),
                    'credit':0.0,
                }

            if self.net_closing_cost > 0:

                debit_lines_net_closing_costs = {
                        'name': 'Net Closing Cost',
                        'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                        'account_id': self.env["account.account"].search(["&", ("code", "=", "68410000"), ("company_id", "=", company_new.id)]).id,
                        'debit': round(self.net_closing_cost, 2),
                        'credit': 0.0
                }
            
            else:
                    
                credit_lines_net_closing_costs = {
                        'name': 'Net Closing Cost',
                        'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                        'account_id': self.env["account.account"].search(["&", ("code", "=", "68410000"), ("company_id", "=", company_new.id)]).id,
                        'debit': 0.0,
                        'credit': round(self.net_closing_cost, 2),
                }

            credit_line_old_loan_items = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "2000402"), ("company_id", "=", company_new.id)]).id,
                'name': 'Old Loan Items',
                'partner_id': self.old_owner.id,
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': 0.0,
                'credit': round(sum_loans, 2),
            }

            net = self.property_cost - sum_loans
            credit_line_net = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "2000401"), ("company_id", "=", company_new.id)]).id,
                'name': 'Net',
                'partner_id': self.old_owner.id,
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': 0.0,
                'credit': round(net, 2),
            }

            credit_lines_new_loan_amount = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", "2000402"), ("company_id", "=", company_new.id)]).id,
                'name': 'New Loan Amount',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': 0.0,
                'credit': round(self.new_loan_amount, 2),
            }

            credit_lines_amount_to_pay_new_owner = {
                'account_id': self.env["account.account"].search(["&", ("code", "=", account_code), ("company_id", "=", company_new.id)]).id,
                'name': 'Amount to Pay',
                'analytic_distribution': {str(self.property_address.analytical_account.id): 100.0},
                'debit': 0.0,
                'credit': round(self.amount_to_pay, 2),
            }

            refinance_entry_lines_new_owner.append(Command.create(debit_lines_amount_to_receive_new_owner))
            refinance_entry_lines_new_owner.append(Command.create(debit_lines_mortgage_cost_refinance))
            refinance_entry_lines_new_owner.append(Command.create(debit_lines_escrow_money_refinance)) 
            refinance_entry_lines_new_owner.append(Command.create(debit_lines_insurance_refinance))
            refinance_entry_lines_new_owner.append(Command.create(debit_lines_taxes_refinance))
            refinance_entry_lines_new_owner.append(Command.create(debit_lines_loan_financial_institution)) 
            refinance_entry_lines_new_owner.append(Command.create(debit_lines_property_cost_refinance))
            refinance_entry_lines_new_owner.append(Command.create(credit_lines_new_loan_amount))
            refinance_entry_lines_new_owner.append(Command.create(credit_lines_amount_to_pay_new_owner))
            if self.net_closing_cost > 0:
                refinance_entry_lines_new_owner.append(Command.create(debit_lines_net_closing_costs))
            elif self.net_closing_cost < 0:
                refinance_entry_lines_new_owner.append(Command.create(credit_lines_net_closing_costs))
            refinance_entry_lines_new_owner.append(Command.create(credit_line_old_loan_items))
            refinance_entry_lines_new_owner.append(Command.create(credit_line_net))


            refinance_entry_new_owner['line_ids'] += refinance_entry_lines_new_owner

            journal_transaction_refinance_new_owner = self.env['account.move'].create(refinance_entry_new_owner)
            journal_transaction_refinance_new_owner.action_post()
            if self.note:
                journal_transaction_refinance_new_owner.message_post(body=self.note)
            attachment_model = self.env["ir.attachment"]
            attachment_payoff_details = attachment_model.browse(self.payoff_details.ids)
            attachment_payoff_details.copy({'res_id': journal_transaction_refinance_new_owner.id, 'res_model': 'account.move'})
        
            attachment_lender_package = attachment_model.browse(self.lender_package.ids)
            attachment_lender_package.copy({'res_id': journal_transaction_refinance_new_owner.id, 'res_model': 'account.move'})

            if loan_items != (sum_loans - self.property_cost) * -1:
                raise ValidationError("Loan Between Related Companies amounts not matching")

            action = {

                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': journal_transaction_refinance_new_owner.id,
                'target': 'current',
            }

            return action


        # EN caso de refinanciamiento
        # 2 Asientos, 1 en el old owner y otro en el new owner
        # los clips y mensajes llenos
