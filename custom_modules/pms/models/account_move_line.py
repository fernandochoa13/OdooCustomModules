# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import  UserError
from odoo.tools.sql import SQL    

import io
import zipfile
import base64
import xlsxwriter

import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = ["account.move.line"]
    
#    check_number = fields.Char(related='move_id.payment_id.check_number', string='Check Number', readonly=True)
    clear_budget = fields.Boolean(related='move_id.clear_budget', string='Cleared', readonly=True)
 
    billable = fields.Boolean(string="Billable")
    invoiced = fields.Many2one(comodel_name="account.move", string="Invoiced")
    markup = fields.Float(string="Markup")
    subproducts = fields.Many2one("product.subproduct", string="Subproduct")
    activity = fields.Many2one("pms.activity.costs", string="Activity")

    cash_date = fields.Date(string="Cash Basis Date", related='move_id.cash_date', store=True)
    partial = fields.Boolean(string="paid in portions", related='move_id.partial', store=True)
    
    # Override fields
    
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Partner',
        compute='_compute_partner_id', inverse='_inverse_partner_id', 
        store=True, readonly=False, precompute=True,
        ondelete='restrict', index=True
    )
    
    def export_pdfs(self):
        for record in self:
            attachment_ids = record.move_id.attachment_ids

            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for attachment in attachment_ids:
                    if attachment.datas:
                        zip_file.writestr(attachment.name, base64.b64decode(attachment.datas))

            zip_buffer.seek(0)

            zip_data = zip_buffer.read()
            zip_data_base64 = base64.b64encode(zip_data).decode('utf-8')

            file_name = f"{record.move_id.name}.zip"

            headers = [
            ('Content-Type', 'application/zip'),
            ('Content-Disposition', f'attachment; filename="{file_name}"')
        ]

            return {
                'type': 'ir.actions.act_url',
                'url': 'data:application/zip;base64,' + zip_data_base64,
                'target': 'new',
                'filename': file_name,
                'headers': headers
            }


    def _check_reconciliation(self):
        # Allow the check to be bypassed by a context key.
        if self.env.context.get('allow_partner_id_change'):
            return

        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                                  "You can just change some non legal fields or you must unreconcile first.\n"
                                  "Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))

    @api.onchange("billable")
    def _onchange_billable(self):
        if self.billable:
            self.markup = self.env['ir.config_parameter'].sudo().get_param('pms.markup')
 
    def create(self, vals_list):
        res = super().create(vals_list)

        for line in res:
            if line.analytic_distribution and line.move_id.state == 'posted':
                _logger.info(f"Creating analytic lines for newly created line: {line.id}")
                # Call the correct method to create the analytic lines
                line._create_analytic_lines()
                _logger.info(f"Successfully created analytic lines for line: {line.id}")

        return res
 
    def write(self, vals):
        res = super().write(vals)
        
        if not self.env.context.get('from_put_off_hold'):
            _logger.info(f"write() called for records: {self.ids}, vals: {vals}")
            for line in self:                
                if line.analytic_distribution and line.move_id.state == 'posted':
                    _logger.info(f"Updating analytic lines for line: {line.id}")
                    analytic_lines = self.env['account.analytic.line'].search([
                        ('move_line_id', '=', line.id)
                    ])
                    _logger.info(f"Found {len(analytic_lines)} analytic lines to delete.")
                    analytic_lines.unlink()

                    line._create_analytic_lines()
                    _logger.info(f"Created new analytic lines for line: {line.id}")
                else:
                    analytic_lines = self.env['account.analytic.line'].search([
                        ('move_line_id', '=', line.id)
                    ])
                    _logger.info(f"Found {len(analytic_lines)} analytic lines to delete.")
                    analytic_lines.unlink()
        return res
    
    # Override account_move_line _unlink_except_posted check to allow deleting analytic lines
    
    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted(self):
        if not self._context.get('force_delete') and any(m.state == 'cancel' for m in self.move_id): # remove posted check?
            raise UserError(_('You cannot delete an item linked to a cancelled entry.'))
        
    def _inverse_analytic_distribution(self):
        return
    
    def _where_calc(self, domain, active_test=True):
        """ In case of cash basis for reports, we need to shadow the table account_move_line to get amounts
        based on cash.
        We also need to get the analytic amounts in the table if we have the analytic grouping on reports.
        """
        query = super()._where_calc(domain, active_test)
        if self.env.context.get('account_report_cash_basis'):
            self.env['account.report']._prepare_lines_for_cash_basis()
            if self.env.context.get('account_report_analytic_groupby'):
                self.env['account.report']._prepare_lines_for_analytic_groupby_with_cash_basis()
                query._tables['account_move_line'] = 'analytic_cash_basis_temp_account_move_line'
            else:
                query._tables['account_move_line'] = 'cash_basis_temp_account_move_line'
        return query
    
    # Inherit account_move_line functions to create and update analytic lines even when posted
 
    # @api.model_create_multi
    # def create(self, vals_list):
    #     lines = super().create(vals_list)
    #     for line in lines:
    #         if line.analytic_distribution:
    #             _logger.info(f"Creating analytic lines for new line: {line.id}")
    #             line._create_analytic_lines()
    #     return lines

    # def write(self, vals):
    #     res = super().write(vals)
    #     _logger.info(f"write() called for records: {self.ids}, vals: {vals}")
        
    #     for line in self:
            
            
            # checks if analytic_distribution is enabled and move is not posted
        #     if line.analytic_distribution and line.move_id.state != 'posted':
                
        #         # get existing analytic lines
        #         analytic_lines = self.env['account.analytic.line'].search([('move_line_id', '=', line.id)])
        #         analytic_lines_ids = analytic_lines.ids
        #         # delete existing analytic lines
        #         analytic_lines.unlink()
                
        #         # create new analytic lines
        #         new_analytic_lines = line._create_analytic_lines()
                
        #         # update move lines with new analytic lines
        #         if analytic_lines_ids and new_analytic_lines:
        #             for old_line_id in analytic_lines_ids:
        #                 new_line = self.env['account.analytic.line'].search([
        #                     ('move_line_id', '=', line.id),
        #                     ('id', 'not in', analytic_lines_ids)
        #                 ], limit=1)
                        
        #                 # update move lines with new analytic lines
        #                 if new_line:
        #                     move_lines_to_update = self.env['account.move.line'].search([
        #                         ('analytic_line_id', '=', old_line_id),
        #                         ('move_id', '=', line.move_id.id)
        #                     ])
        #                     for move_line_to_update in move_lines_to_update:
        #                         move_line_to_update.analytic_line_id = new_line.id
        # return res

        
        
    #  backup account_move
            
    # @api.onchange('invoice_line_ids')
    # def _onchange_invoice_line_ids(self):
    #     for line in self.invoice_line_ids:
    #         _logger.info(f"_onchange_invoice_line_ids is running...")
    #         if line.analytic_distribution:
    #             _logger.info(f"Processing line: {line.id}")
    #             _logger.info(f"Computing totals for line: {line.id}, quantity: {line.quantity}, price_subtotal: {line.price_subtotal}")
                
    #             analytic_lines = self.env['account.analytic.line'].search([
    #                 ('move_line_id', '=', line.id)
    #             ])
    #             _logger.info(f"Found {len(analytic_lines)} analytic lines to delete.")
    #             analytic_lines.unlink()

    #             line._create_analytic_lines()
    #             _logger.info(f"Created new analytic lines for line: {line.id}")

    #             line._compute_totals()
                
    """
        account_move_line -> account_analytic_line fields: 
            product_id -> product_id,
            subproducts, 
            activity, 
            name -> name, 
            account_id -> general_account_id, 
            analytic_distribution -> account_id
            billable, 
            markup, 
            price_unit, 
            quantity -> unit_amount,
            price_unit, 
            discount, 
            tax_ids, 
            price_subtotal -> amount?, 
            purchase_order_id
    """
    
  


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def export_to_xlsx(self, options, response=None):
        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self.name[:31])
        
        default_bg_style = workbook.add_format({'bg_color': '#F5F5F5'})
        
        # ====================================================================
        # Change starts here
        
        company_header_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'font_size': 14,
            'bg_color': '#F5F5F5',
        })
        
        report_title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 14,
            'bg_color': '#F5F5F5',
        })

        header_format = workbook.add_format({
            'align': 'left',
            'font_size': 12,
            'bg_color': '#F5F5F5',
        })

        company = self.env.company
        partner = company.partner_id
        
        report_title = self.name or options.get('name') or options.get('string') or 'Financial Report'
        report_date = options.get('date', {}).get('string', options.get('date_to', 'N/A'))

        y_offset = 0

        total_colspan = 1 + len(options['columns']) + (1 if options.get('show_growth_comparison') else 0)

        write_with_colspan(sheet, 0, y_offset, company.name, total_colspan, company_header_format)
        y_offset += 1
        
        if partner.street:
            write_with_colspan(sheet, 0, y_offset, partner.street, total_colspan, header_format)
            y_offset += 1
        if partner.street2:
            write_with_colspan(sheet, 0, y_offset, partner.street2, total_colspan, header_format)
            y_offset += 1
        
        city_line = ''
        if partner.city:
            city_line += partner.city
        if partner.state_id:
            city_line += f", {partner.state_id.name}" if city_line else partner.state_id.name
        if partner.zip:
            city_line += f" {partner.zip}" if city_line else partner.zip
        if city_line:
            write_with_colspan(sheet, 0, y_offset, city_line, total_colspan, header_format)
            y_offset += 1

        if partner.country_id:
            write_with_colspan(sheet, 0, y_offset, partner.country_id.name, total_colspan, header_format)
            y_offset += 1
            
        y_offset += 1

        write_with_colspan(sheet, 0, y_offset, report_title, total_colspan, report_title_format)
        y_offset += 1
        
        y_offset += 1
        
        # Change ends here
        # ====================================================================

        # Set the first column width to 50
        sheet.set_column(0, 0, 50, default_bg_style)
        # Set the second column width to half of the first column
        sheet.set_column(1, 1, 25, default_bg_style)
        
        # Apply the default background style to all columns to remove white gaps
        sheet.set_column(2, 100, None, default_bg_style)

        x_offset = 1 # 1 and not 0 to leave space for the line name
        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd', 'bg_color': '#F5F5F5'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd', 'bg_color': '#F5F5F5'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'bg_color': '#F5F5F5'})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'bg_color': '#F5F5F5'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'bg_color': '#F5F5F5'})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666', 'bg_color': '#F5F5F5'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666', 'bg_color': '#F5F5F5'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1, 'bg_color': '#F5F5F5'})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'bg_color': '#F5F5F5'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'bg_color': '#F5F5F5'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'bg_color': '#F5F5F5'})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1, 'bg_color': '#F5F5F5'})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'bg_color': '#F5F5F5'})

        print_mode_self = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)
        print_options = print_mode_self._get_options(previous_options=options)
        lines = self._filter_out_folded_children(print_mode_self._get_lines(print_options))

        # Add headers.
        # For this, iterate in the same way as done in main_table_header template
        column_headers_render_data = self._get_column_headers_render_data(print_options)
        for header_level_index, header_level in enumerate(print_options['column_headers']):
            for header_to_render in header_level * column_headers_render_data['level_repetitions'][header_level_index]:
                colspan = header_to_render.get('colspan', column_headers_render_data['level_colspan'][header_level_index])
                write_with_colspan(sheet, x_offset, y_offset, header_to_render.get('name', ''), colspan, title_style)
                x_offset += colspan
            if print_options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset, '%', 1, title_style)
            y_offset += 1
            x_offset = 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, subheader.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1
        x_offset = 1

        for column in print_options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset, column.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1

        if print_options.get('order_column'):
            lines = self._sort_lines(lines, print_options)

        # Add lines.
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            columns = lines[y]['columns']
            if print_options['show_growth_comparison'] and 'growth_comparison_data' in lines[y]:
                columns += [lines[y].get('growth_comparison_data')]
            for x, column in enumerate(columns, start=1):
                cell_type, cell_value = self._get_cell_type_value(column)
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': self.get_default_report_filename('xlsx'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }



    @api.model
    def _prepare_lines_for_analytic_groupby_with_cash_basis(self):
        """ Prepare the analytic_cash_basis_temp_account_move_line
 
        This method should be used once before all the SQL queries using the
        table account_move_line for the analytic columns for the financial reports.
        It will create a new table with the schema of account_move_line table, but with
        the data from account_analytic_line and cash_basis_temp_account_move_line.
 
        We will replace the values of the lines of the table cash_basis_temp_account_move_line
        with the values of the analytic lines linked to these, but we will make the prorata
        of the amounts with the portion of the amount paid.
        """
 
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name='analytic_cash_basis_temp_account_move_line'")
        if self.env.cr.fetchone():
            return
 
        line_fields = self.env['account.move.line'].fields_get()
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        stored_fields = {f[0] for f in self.env.cr.fetchall() if f[0] in line_fields}
        changed_equivalence_dict = {
            "balance": 'CASE WHEN aml.balance != 0 THEN -aal.amount * cash_basis_aml.balance / aml.balance ELSE 0 END',
            "amount_currency": 'CASE WHEN aml.amount_currency != 0 THEN -aal.amount * cash_basis_aml.amount_currency / aml.amount_currency ELSE 0 END',
            "amount_residual": 'CASE WHEN aml.amount_residual != 0 THEN -aal.amount * cash_basis_aml.amount_residual / aml.amount_residual ELSE 0 END',
            "date": 'cash_basis_aml.date',
            "account_id": 'aal.general_account_id',
            "partner_id": 'aal.partner_id',
            "debit": 'CASE WHEN (aml.balance < 0) THEN -aal.amount * cash_basis_aml.balance / aml.balance ELSE 0 END',
            "credit": 'CASE WHEN (aml.balance > 0) THEN -aal.amount * cash_basis_aml.balance / aml.balance ELSE 0 END',
        }


        selected_fields = []
        for fname in stored_fields:
            if fname in changed_equivalence_dict:
                selected_fields.append(f'{changed_equivalence_dict[fname]} AS {fname}')
            elif fname == 'analytic_distribution':
                selected_fields.append(f'to_jsonb(aal.account_id) AS "account_move_line.analytic_distribution"')
            else:
                selected_fields.append(f'aml.{fname} AS {fname}')
        field_string = ", ".join(field_name for field_name in stored_fields)
        selected_fields_string = ', '.join(selected_fields)
 
        query = SQL(
            f"""
            -- Create a temporary table
            CREATE TABLE IF NOT EXISTS analytic_cash_basis_temp_account_move_line AS
                TABLE account_move_line WITH NO DATA;
 
            INSERT INTO analytic_cash_basis_temp_account_move_line ({field_string})
            SELECT {selected_fields_string}
            FROM ONLY cash_basis_temp_account_move_line cash_basis_aml
            JOIN ONLY account_move_line aml ON aml.id = cash_basis_aml.id
            JOIN account_analytic_line aal ON aml.id = aal.move_line_id;
 
            -- Create a supporting index to avoid seq.scans
            CREATE INDEX IF NOT EXISTS analytic_cash_basis_temp_account_move_line__composite_idx ON analytic_cash_basis_temp_account_move_line (analytic_distribution, journal_id, date, company_id);
            -- Update statistics for correct planning
            ANALYZE analytic_cash_basis_temp_account_move_line;
        """,
        )
        self.env.cr.execute(query)
        _logger.info("Query loaded")
