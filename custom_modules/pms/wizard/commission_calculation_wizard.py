# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64
import io
import logging

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

_logger = logging.getLogger(__name__)


class CommissionCalculationWizard(models.TransientModel):
    _name = 'commission.calculation.wizard'
    _description = 'Commission Calculation Wizard'

    quickbooks_file = fields.Binary(
        string='QuickBooks Journal Excel File',
        required=True,
        help='Upload the Excel file exported from QuickBooks journal'
    )
    quickbooks_filename = fields.Char(string='File Name')
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        default=3.0,
        required=True,
        help='Management commission rate as percentage (e.g., 3.0 for 3%)'
    )
    quickbooks_output_file = fields.Binary(string='QuickBooks Import File', readonly=True)
    quickbooks_output_filename = fields.Char(string='QuickBooks File Name', readonly=True)
    odoo_output_file = fields.Binary(string='Odoo Import File', readonly=True)
    odoo_output_filename = fields.Char(string='Odoo File Name', readonly=True)

    def action_process_file(self):
        """Process the uploaded QuickBooks file and generate output files"""
        self.ensure_one()
        
        if not pd:
            raise UserError(_("Pandas library is required. Please install it using: pip install pandas"))
        
        if not HAS_OPENPYXL:
            raise UserError(_("Openpyxl library is required. Please install it using: pip install openpyxl"))
        
        if not self.quickbooks_file:
            raise ValidationError(_("Please upload a QuickBooks Excel file."))
        
        # Decode the uploaded file
        try:
            file_content = base64.b64decode(self.quickbooks_file)
            excel_file = io.BytesIO(file_content)
            
            # Read Excel file - try to find the header row
            # QuickBooks exports often have title rows before the actual headers
            df = None
            header_row = 0
            
            # Try reading with different header rows (0, 1, 2, 3)
            for i in range(4):
                try:
                    excel_file.seek(0)
                    test_df = pd.read_excel(excel_file, engine='openpyxl', header=i)
                    # Check if this looks like a header row (has Debit, Credit, Date, etc.)
                    cols_lower = [str(c).lower() for c in test_df.columns]
                    has_debit = any('debit' in c for c in cols_lower)
                    has_credit = any('credit' in c for c in cols_lower)
                    has_date = any('date' in c for c in cols_lower)
                    
                    if has_debit or has_credit or has_date:
                        df = test_df
                        header_row = i
                        _logger.info(f"Found header row at index {i}")
                        break
                except Exception as e:
                    _logger.warning(f"Failed to read with header={i}: {str(e)}")
                    continue
            
            # If still no good header found, try default
            if df is None:
                excel_file.seek(0)
                df = pd.read_excel(excel_file, engine='openpyxl')
            
            # Clean up column names - remove "Unnamed:" prefixes and trim whitespace
            df.columns = [str(col).strip() if not str(col).startswith('Unnamed:') else '' for col in df.columns]
            
            # Check if we have valid column names or if they're all unnamed/empty
            has_valid_columns = any(
                'debit' in str(col).lower() or 
                'credit' in str(col).lower() or 
                'date' in str(col).lower() or
                'memo' in str(col).lower() or
                'description' in str(col).lower()
                for col in df.columns
            )
            
            # If we still have unnamed columns or no valid columns, try to infer from data rows
            if not has_valid_columns or any('Unnamed' in str(col) or str(col).strip() == '' for col in df.columns):
                _logger.info("Attempting to find headers in data rows")
                # Search through first few rows to find one that looks like headers
                for row_idx in range(min(5, len(df))):
                    row_values = [str(val).strip() if pd.notna(val) else '' for val in df.iloc[row_idx]]
                    row_lower = [v.lower() for v in row_values]
                    # Check if this row contains header-like values
                    if (any('debit' in v for v in row_lower) or 
                        any('credit' in v for v in row_lower) or
                        any('date' in v for v in row_lower) or
                        any('memo' in v for v in row_lower) or
                        any('transaction' in v for v in row_lower)):
                        # Use this row as headers
                        df.columns = row_values
                        df = df.iloc[row_idx+1:].reset_index(drop=True)
                        _logger.info(f"Found headers in row {row_idx}: {row_values}")
                        break
            
            _logger.info(f"Processing Excel file with {len(df)} rows")
            _logger.info(f"Columns found: {df.columns.tolist()}")
            
            # Process the data
            quickbooks_data, odoo_data = self._process_data(df)
            
            # Generate output files
            self._generate_quickbooks_file(quickbooks_data)
            self._generate_odoo_file(odoo_data)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'commission.calculation.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
                'context': {'form_view_initial_mode': 'readonly'},
            }
            
        except Exception as e:
            _logger.error(f"Error processing file: {str(e)}", exc_info=True)
            raise UserError(_("Error processing file: %s") % str(e))
    
    def _process_data(self, df):
        """Process the dataframe and calculate commissions"""
        quickbooks_lines = []
        odoo_lines = []
        
        # Try to identify columns automatically (case-insensitive and flexible)
        amount_col = None
        debit_col = None
        credit_col = None
        account_col = None
        property_col = None
        date_col = None
        description_col = None
        memo_col = None
        item_class_col = None
        fullname_col = None  # Column G - fullname column
        
        # Search for common column names (case-insensitive)
        for col in df.columns:
            col_lower = str(col).strip().lower()
            col_original = str(col).strip()
            
            # Amount columns - prioritize Debit and Credit separately
            if 'debit' in col_lower:
                debit_col = col_original
            elif 'credit' in col_lower:
                credit_col = col_original
            elif 'amount' in col_lower and amount_col is None:
                amount_col = col_original
            
            # Account column
            if 'account' in col_lower:
                account_col = col_original
            
            # Fullname column (Column G) - this is the key column for filtering P.M. entries
            # Check for various possible names for this column
            # Exact match for "Full name" (with space) is most common in QuickBooks exports
            if col_lower == 'full name' or col_lower == 'fullname':
                fullname_col = col_original
            elif 'fullname' in col_lower or 'full name' in col_lower:
                if fullname_col is None:
                    fullname_col = col_original
            
            # Property/Address columns - check multiple possibilities
            if 'item class' in col_lower or 'itemclass' in col_lower:
                item_class_col = col_original
            elif 'memo' in col_lower or 'description' in col_lower:
                if memo_col is None:
                    memo_col = col_original
            elif 'property' in col_lower or ('address' in col_lower and property_col is None):
                property_col = col_original
            
            # Date column
            if 'date' in col_lower or 'transaction date' in col_lower:
                date_col = col_original
        
        # Use Debit or Credit if Amount not found
        if not amount_col:
            if debit_col and credit_col:
                # We'll use both and calculate net amount
                amount_col = 'debit_credit_net'
            elif debit_col:
                amount_col = debit_col
            elif credit_col:
                amount_col = credit_col
            else:
                raise ValidationError(_("Could not identify amount column in the Excel file. Please ensure the file has an 'Amount', 'Debit', or 'Credit' column. Found columns: %s") % ', '.join(df.columns.tolist()))
        
        # Use Item Class or Memo for property identification
        if not property_col:
            property_col = item_class_col or memo_col or description_col
        
        # Log detected columns for debugging
        _logger.info(f"Detected columns - fullname: {fullname_col}, memo: {memo_col}, debit: {debit_col}, credit: {credit_col}, date: {date_col}")
        
        # If fullname column not found, try to use column index 6 (Column G, 0-indexed)
        if not fullname_col and len(df.columns) > 6:
            fullname_col = df.columns[6]  # Column G (0-indexed = 6)
            _logger.info(f"Using column index 6 as fullname column: {fullname_col}")
        
        commission_rate = self.commission_rate / 100.0
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                # Create a copy of the original row for QuickBooks output
                quickbooks_line = {}
                for col in df.columns:
                    quickbooks_line[col] = row.get(col, '')
                
                # Check if this row has "P.M." in the fullname column (Column G)
                fullname_value = str(row.get(fullname_col, '')).strip() if fullname_col else ''
                fullname_upper = fullname_value.upper()
                
                # Check if it's a P.M. entry (rental income)
                # But exclude entries that already have "Tarifa" or "Management Fee" (existing commission lines)
                is_pm_entry = (
                    'P.M.' in fullname_upper and 
                    'TARIFA' not in fullname_upper and
                    'MANAGEMENT FEE' not in fullname_upper and
                    'MANAGEMENT' not in fullname_upper  # Exclude existing commission lines
                ) if fullname_value else False
                
                # Also check memo/description columns as fallback if fullname doesn't have P.M.
                if not is_pm_entry:
                    memo_value = str(row.get(memo_col, '')).strip() if memo_col else ''
                    memo_upper = memo_value.upper()
                    if 'P.M.' in memo_upper and 'TARIFA' not in memo_upper and 'MANAGEMENT FEE' not in memo_upper and 'MANAGEMENT' not in memo_upper:
                        is_pm_entry = True
                        _logger.info(f"Found P.M. in memo column for row {idx}")
                
                # As a last resort, check all columns for "P.M." pattern
                if not is_pm_entry:
                    for col in df.columns:
                        col_value = str(row.get(col, '')).strip()
                        col_upper = col_value.upper()
                        if 'P.M.' in col_upper and 'TARIFA' not in col_upper and 'MANAGEMENT FEE' not in col_upper and 'MANAGEMENT' not in col_upper:
                            is_pm_entry = True
                            _logger.info(f"Found P.M. in column '{col}' for row {idx}")
                            # If we found it in a column that might be fullname, update fullname_col
                            if not fullname_col and ('name' in str(col).lower() or col == df.columns[6] if len(df.columns) > 6 else False):
                                fullname_col = col
                            break
                
                if is_pm_entry:
                    _logger.info(f"Processing P.M. entry at row {idx}, fullname: {fullname_value}")
                
                # Get amount value - handle both Debit and Credit columns
                # For rental income, the amount is typically in the Credit column (positive)
                if amount_col == 'debit_credit_net':
                    debit_val = self._safe_float(row.get(debit_col, 0))
                    credit_val = self._safe_float(row.get(credit_col, 0))
                    # For rental income entries, use credit value (income is credit)
                    amount = credit_val if credit_val > 0 else debit_val
                    amount_abs = abs(amount)
                else:
                    amount = self._safe_float(row.get(amount_col, 0))
                    amount_abs = abs(amount)
                    # If we have separate debit/credit columns, prefer credit for rental income
                    if is_pm_entry and credit_col and debit_col:
                        credit_val = self._safe_float(row.get(credit_col, 0))
                        if credit_val > 0:
                            amount_abs = credit_val
                
                # Always add the original line to QuickBooks output
                quickbooks_lines.append(quickbooks_line)
                
                # If it's a P.M. entry (rental income), calculate commission and insert new row
                if is_pm_entry and amount_abs > 0:
                    commission_amount = round(amount_abs * commission_rate, 2)
                    
                    # Extract property address - prioritize Item Class column (most reliable)
                    property_name = ''
                    
                    # First, try Item Class column (this contains property addresses)
                    if item_class_col:
                        item_class_value = str(row.get(item_class_col, '')).strip()
                        if item_class_value:
                            property_name = item_class_value
                    
                    # If Item Class is empty, try memo/description
                    if not property_name:
                        memo_value = str(row.get(memo_col, '')).strip() if memo_col else ''
                        if memo_value:
                            # Format: "October - P.M. - 1045 9TH Ave" or similar
                            if ' - ' in memo_value:
                                parts = memo_value.split(' - ')
                                if len(parts) >= 3:
                                    property_name = parts[-1].strip()  # Get the last part (address)
                                else:
                                    property_name = memo_value
                            else:
                                property_name = memo_value
                    
                    # Try property column as last resort
                    if not property_name and property_col:
                        property_name = str(row.get(property_col, '')).strip()
                    
                    # Create commission line for QuickBooks - INSERT NEW ROW
                    commission_line = quickbooks_line.copy()
                    
                    # Set commission amount in the appropriate column
                    # Commission should be in Credit column (as requested)
                    if amount_col == 'debit_credit_net':
                        # For rental income (credit), commission goes in Credit
                        commission_line[debit_col] = 0
                        commission_line[credit_col] = commission_amount
                    elif debit_col and credit_col:
                        # We have both columns - commission goes in Credit
                        commission_line[debit_col] = 0
                        commission_line[credit_col] = commission_amount
                    elif credit_col:
                        # Commission goes in Credit column
                        commission_line[credit_col] = commission_amount
                        if debit_col:
                            commission_line[debit_col] = 0
                    elif debit_col:
                        # If only debit column exists, we'll need to use it but this is not ideal
                        # Set debit to 0 and try to create credit column
                        commission_line[debit_col] = 0
                        # Note: This case should not happen in QuickBooks exports
                    else:
                        commission_line[amount_col] = commission_amount
                    
                    # Update description/account for commission
                    # Description: "Management Fee - [Property Address]"
                    commission_description = f"Management Fee - {property_name}" if property_name else "Management Fee"
                    
                    # Update Full name column to identify this as a commission line
                    if fullname_col:
                        # Update Full name to indicate this is a commission/tariff entry
                        original_fullname = str(row.get(fullname_col, '')).strip()
                        # Change from "Orkam Inv October - P.M." to "Orkam Inv Management Fee - P.M."
                        if ' - P.M.' in original_fullname:
                            commission_line[fullname_col] = original_fullname.replace(' - P.M.', ' Management Fee - P.M.')
                        elif 'P.M.' in original_fullname:
                            commission_line[fullname_col] = original_fullname.replace('P.M.', 'Management Fee - P.M.')
                        else:
                            commission_line[fullname_col] = f"{original_fullname} Management Fee - P.M."
                    
                    # Update memo/description column
                    if memo_col:
                        commission_line[memo_col] = commission_description
                    elif description_col:
                        commission_line[description_col] = commission_description
                    
                    # Update account if available
                    if account_col:
                        # Keep the same account structure, or set to management fee account
                        # For now, we'll keep the original account or leave it for manual adjustment
                        pass
                    
                    # Insert the commission line right after the original P.M. entry
                    quickbooks_lines.append(commission_line)
                    
                    # Create Odoo line
                    date_value = row.get(date_col, '') if date_col else ''
                    odoo_line = self._create_odoo_line(
                        property_name,
                        amount_abs,  # Use absolute amount for rental
                        commission_amount,
                        date_value,
                        commission_description
                    )
                    if odoo_line:
                        odoo_lines.append(odoo_line)
                        _logger.info(f"Created Odoo line for property: {property_name}, commission: {commission_amount}")
                    else:
                        _logger.warning(f"Failed to create Odoo line for row {idx}")
                        
            except Exception as e:
                _logger.warning(f"Error processing row {idx}: {str(e)}", exc_info=True)
                continue
        
        _logger.info(f"Processed {len(quickbooks_lines)} QuickBooks lines and {len(odoo_lines)} Odoo lines")
        
        # If no Odoo lines were created but we have QuickBooks lines with commissions, 
        # create at least one Odoo line as a template
        if not odoo_lines and quickbooks_lines:
            _logger.warning("No Odoo lines created. This might indicate no P.M. entries were found.")
            # Try to create a sample line anyway
            sample_line = self._create_odoo_line(
                '',
                0,
                0,
                fields.Date.today(),
                'Management Fee'
            )
            if sample_line:
                odoo_lines.append(sample_line)
        
        return quickbooks_lines, odoo_lines
    
    def _create_odoo_line(self, property_name, rental_amount, commission_amount, date_value, description):
        """Create a line for Odoo import file with proper format"""
        # Find property in Odoo by name
        property_obj = None
        analytic_account_name = None
        
        if property_name:
            # Try to find property by name (fuzzy matching)
            property_obj = self.env['pms.property'].search([
                ('name', 'ilike', property_name)
            ], limit=1)
            
            if not property_obj:
                # Try searching in analytic accounts
                analytic_account = self.env['account.analytic.account'].search([
                    ('name', 'ilike', property_name)
                ], limit=1)
                if analytic_account:
                    analytic_account_name = analytic_account.name
                    property_obj = self.env['pms.property'].search([
                        ('analytical_account', '=', analytic_account.id)
                    ], limit=1)
        
        if property_obj and property_obj.analytical_account:
            analytic_account_name = property_obj.analytical_account.name
        
        # Get company name
        company_name = self.env.company.name if self.env.company else ''
        
        # Format date properly
        if date_value:
            if isinstance(date_value, str):
                try:
                    # Try to parse the date string
                    from datetime import datetime
                    date_obj = datetime.strptime(str(date_value).split()[0], '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                except:
                    formatted_date = str(date_value).split()[0] if ' ' in str(date_value) else str(date_value)
            else:
                formatted_date = str(date_value).split()[0] if ' ' in str(date_value) else str(date_value)
        else:
            formatted_date = fields.Date.today().strftime('%Y-%m-%d')
        
        # Create Odoo import line with proper structure
        # Note: Account column is left empty as it's dynamic and requires manual input
        odoo_line = {
            'company': company_name,
            'date': formatted_date,
            'journal': '',  # Leave empty for manual input
            'account': '',  # Dynamic - requires manual input (e.g., "renta, Lincoln")
            'analytic_account': analytic_account_name or '',
            'property': property_name or '',
            'description': description or f'Management Fee - {property_name}',
            'debit': 0,
            'credit': commission_amount,  # Commission goes in Credit column
            'rental_amount': rental_amount,
            'commission_rate': f'{self.commission_rate}%',
        }
        
        return odoo_line
    
    def _safe_float(self, value):
        """Safely convert value to float, handling European number format"""
        if pd.isna(value):
            return 0.0
        try:
            # Convert to string first
            str_value = str(value).strip()
            if not str_value or str_value == '':
                return 0.0
            
            # Handle European number format (e.g., "2.297,00" = 2297.00)
            # Check if it uses . as thousands separator and , as decimal
            if '.' in str_value and ',' in str_value:
                # Count occurrences to determine format
                last_dot = str_value.rfind('.')
                last_comma = str_value.rfind(',')
                if last_dot > last_comma:
                    # Format: 2.297,00 (European)
                    str_value = str_value.replace('.', '').replace(',', '.')
                else:
                    # Format: 2,297.00 (US) - just remove thousands separator
                    str_value = str_value.replace(',', '')
            elif ',' in str_value:
                # Could be European decimal or US thousands - check position
                if str_value.count(',') == 1 and len(str_value.split(',')[1]) <= 2:
                    # Likely European decimal (e.g., "2297,00")
                    str_value = str_value.replace(',', '.')
                else:
                    # Likely US thousands separator
                    str_value = str_value.replace(',', '')
            
            return float(str_value)
        except (ValueError, TypeError, AttributeError):
            return 0.0
    
    def _generate_quickbooks_file(self, data):
        """Generate QuickBooks import Excel file"""
        if not data:
            raise ValidationError(_("No data to export for QuickBooks file."))
        
        try:
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            try:
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Journal Entries')
            except Exception:
                # Fallback if openpyxl fails
                output.seek(0)
                with pd.ExcelWriter(output) as writer:
                    df.to_excel(writer, index=False, sheet_name='Journal Entries')
            
            output.seek(0)
            file_content = output.read()
            
            # Encode and save
            self.quickbooks_output_file = base64.b64encode(file_content)
            self.quickbooks_output_filename = f'QuickBooks_Import_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
        except Exception as e:
            _logger.error(f"Error generating QuickBooks file: {str(e)}", exc_info=True)
            raise UserError(_("Error generating QuickBooks file: %s") % str(e))
    
    def _generate_odoo_file(self, data):
        """Generate Odoo import Excel file"""
        if not data:
            _logger.warning("No Odoo data to export. This usually means no P.M. entries were found in the file.")
            # Create an empty file with headers for reference
            empty_data = [{
                'company': '',
                'date': '',
                'journal': '',
                'account': '',
                'analytic_account': '',
                'property': '',
                'description': '',
                'debit': 0,
                'credit': 0,
                'rental_amount': 0,
                'commission_rate': f'{self.commission_rate}%',
            }]
            data = empty_data
            _logger.info("Generated empty Odoo file template with headers")
        
        try:
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = io.BytesIO()
            try:
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Commission Lines')
            except Exception:
                # Fallback if openpyxl fails
                output.seek(0)
                with pd.ExcelWriter(output) as writer:
                    df.to_excel(writer, index=False, sheet_name='Commission Lines')
            
            output.seek(0)
            file_content = output.read()
            
            # Encode and save
            self.odoo_output_file = base64.b64encode(file_content)
            self.odoo_output_filename = f'Odoo_Import_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            
        except Exception as e:
            _logger.error(f"Error generating Odoo file: {str(e)}", exc_info=True)
            raise UserError(_("Error generating Odoo file: %s") % str(e))

