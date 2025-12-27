# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError

from datetime import timedelta

class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[
        ('account.move.in_invoice', "Vendor bill"),
        ('account.move.out_invoice', 'Customer invoice'),
        ('account.move.in_refund', 'Vendor Credit Note'),
        ('account.move.out_refund', "Credit note")])

    def create_record(self, documents=None):
        rv = super(WorkflowActionRuleAccount, self).create_record(documents=documents)
        if self.create_model == 'account.move.out_invoice':
            invoice_type = self.create_model.split('.')[2]
            new_obj = None
            invoice_ids = []
            # selected_companies = self.env.companies  # Get the selected companies

            for document in documents:
                doc_res_id = document.res_id
                doc_res_model = document.res_model
                partner = self.partner_id or document.partner_id

                # Check if customer's company is in the selected companies
                # if document.customer and document.customer.company_id not in selected_companies:
                #     raise UserError(_(
                #         "Cannot create invoice/bill. The customer's company (%s) is not among the selected companies: %s."
                #     ) % (
                #         document.customer.company_id.name,
                #         ", ".join(selected_companies.mapped('name'))
                #     ))
                    
                if doc_res_model == 'account.move' and doc_res_id:
                    new_obj = self.env['account.move'].browse(document.res_id)
                    if new_obj.statement_line_id:
                        new_obj.suspense_statement_line_id = new_obj.statement_line_id.id
                    invoice_ids.append(new_obj.id)
                else:
                    new_obj = self.env['account.journal'].with_context(
                        default_move_type=invoice_type)._create_document_from_attachment(
                        attachment_ids=document.attachment_id.id)

                    if doc_res_model == 'account.move.line' and doc_res_id:
                        new_obj.document_request_line_id = doc_res_id
                    if partner:
                        new_obj.partner_id = partner
                        new_obj._onchange_partner_id()

                vals = {
                    'invoice_date': fields.Date.today(),
                }
                if document.date:
                    vals['contractor_date'] = document.date
                if document.partner_id and document.partner_id.contractor_payment_terms:
                    vals['invoice_payment_term_id'] = document.partner_id.contractor_payment_terms.id
                if document.invoice_link:
                    vals['invoice_link_docs'] = document.invoice_link
                if document.invoice_number:
                    vals['payment_reference'] = document.invoice_number
                    vals['ref'] = document.invoice_number
                if document.amount or document.concept:
                    line_vals = {
                        'quantity': 1,
                        'name': document.concept or '',
                        'price_unit': document.amount or 0.0,
                    }
                    vals['invoice_line_ids'] = [(0, 0, line_vals)]
                if document.customer:
                    vals['partner_shipping_id'] = document.customer.id

                if vals:
                    new_obj.write(vals)

                if not (doc_res_model == 'account.move' and doc_res_id):
                    new_obj._compute_name()
                    new_obj._compute_amount()
                    new_obj._check_balanced()

                    # the 'no_document' key in the context indicates that this ir_attachment has already a
                    # documents.document and a new document shouldn't be automatically generated.
                    document.attachment_id.with_context(no_document=True).write({
                        'res_model': 'account.move',
                        'res_id': new_obj.id,
                    })
                invoice_ids.append(new_obj.id)

            context = dict(self._context, default_move_type=invoice_type)
            if len(invoice_ids) == 1:
                record = new_obj or self.env['account.move'].browse(invoice_ids[0])
                view_id = record.get_formview_id() if record else self.env.ref('account.view_move_form').id
                action = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'name': "Invoices",
                    'view_mode': 'form',
                    'views': [(view_id, "form")],
                    'res_id': invoice_ids[0],
                    'view_id': view_id,
                    'context': context,
                }
            else:
                action = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'name': "Invoices",
                    'view_id': False,
                    'view_mode': 'tree,form',
                    'views': [(False, "list"), (False, "form")],
                    'domain': [('id', 'in', invoice_ids)],
                    'context': context,
                }
            return action
        elif self.create_model == 'account.move.in_invoice':
            invoice_type = self.create_model.split('.')[2]
            new_obj = None
            invoice_ids = []
            for document in documents:
                doc_res_id = document.res_id
                doc_res_model = document.res_model
                partner = self.partner_id or document.partner_id
                if doc_res_model == 'account.move' and doc_res_id:
                    new_obj = self.env['account.move'].browse(document.res_id)
                    if new_obj.statement_line_id:
                        new_obj.suspense_statement_line_id = new_obj.statement_line_id.id
                    invoice_ids.append(new_obj.id)
                else:
                    new_obj = self.env['account.journal'].with_context(
                        default_move_type=invoice_type)._create_document_from_attachment(
                        attachment_ids=document.attachment_id.id)

                    if doc_res_model == 'account.move.line' and doc_res_id:
                        new_obj.document_request_line_id = doc_res_id
                    if partner:
                        new_obj.partner_id = partner
                        new_obj._onchange_partner_id()

                vals = {}
                if document.date:
                    vals['invoice_date'] = document.date
                else:
                    vals['invoice_date'] = fields.Date.today() + timedelta(days=7) # default to 7 days from now
                if document.invoice_number:
                    vals['payment_reference'] = document.invoice_number
                    vals['ref'] = document.invoice_number
                if document.amount or document.concept:
                    line_vals = {
                        'quantity': 1,
                        'name': document.concept or '',
                        'price_unit': document.amount or 0.0,
                    }
                    vals['invoice_line_ids'] = [(0, 0, line_vals)]
                if document.customer:
                    vals['partner_shipping_id'] = document.customer.id
                if document.payment_type:
                    vals['payment_type_bills'] = document.payment_type

                if vals:
                    new_obj.write(vals)

                if not (doc_res_model == 'account.move' and doc_res_id):
                    new_obj._compute_name()
                    new_obj._compute_amount()
                    new_obj._check_balanced()

                    # the 'no_document' key in the context indicates that this ir_attachment has already a
                    # documents.document and a new document shouldn't be automatically generated.
                    document.attachment_id.with_context(no_document=True).write({
                        'res_model': 'account.move',
                        'res_id': new_obj.id,
                    })
                invoice_ids.append(new_obj.id)

            context = dict(self._context, default_move_type=invoice_type)
            if len(invoice_ids) == 1:
                record = new_obj or self.env['account.move'].browse(invoice_ids[0])
                view_id = record.get_formview_id() if record else self.env.ref('account.view_move_form').id
                action = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'name': "Bills",
                    'view_mode': 'form',
                    'views': [(view_id, "form")],
                    'res_id': invoice_ids[0],
                    'view_id': view_id,
                    'context': context,
                }
            else:
                action = {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.move',
                    'name': "Bills",
                    'view_id': False,
                    'view_mode': 'tree,form',
                    'views': [(False, "list"), (False, "form")],
                    'domain': [('id', 'in', invoice_ids)],
                    'context': context,
                }
            return action
        else:
            invoice_type = self.create_model.split('.')[2]
            new_obj = None
            invoice_ids = []
            for document in documents:
                doc_res_id = document.res_id
                doc_res_model = document.res_model
                partner = self.partner_id or document.partner_id
                if doc_res_model == 'account.move' and doc_res_id:
                    new_obj = self.env['account.move'].browse(document.res_id)
                    if new_obj.statement_line_id:
                        new_obj.suspense_statement_line_id = new_obj.statement_line_id.id
                    invoice_ids.append(new_obj.id)
                    continue
                new_obj = self.env['account.journal'].with_context(default_move_type=invoice_type)._create_document_from_attachment(attachment_ids=document.attachment_id.id)
                if doc_res_model == 'account.move.line' and doc_res_id:
                    new_obj.document_request_line_id = doc_res_id
                if partner:
                    new_obj.partner_id = partner
                    new_obj._onchange_partner_id()
                # the 'no_document' key in the context indicates that this ir_attachment has already a
                # documents.document and a new document shouldn't be automatically generated.
                document.attachment_id.with_context(no_document=True).write({
                    'res_model': 'account.move',
                    'res_id': new_obj.id,
                })
                invoice_ids.append(new_obj.id)

            context = dict(self._context, default_move_type=invoice_type)
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'name': "Invoices",
                'view_id': False,
                'view_mode': 'tree',
                'views': [(False, "list"), (False, "form")],
                'domain': [('id', 'in', invoice_ids)],
                'context': context,
            }
            if len(invoice_ids) == 1:
                record = new_obj or self.env['account.move'].browse(invoice_ids[0])
                view_id = record.get_formview_id() if record else False
                action.update({
                    'view_mode': 'form',
                    'views': [(view_id, "form")],
                    'res_id': invoice_ids[0],
                    'view_id': view_id,
                })
            return action
        
        return rv
