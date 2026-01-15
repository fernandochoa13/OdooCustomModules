from odoo import models, fields, api
from odoo.exceptions import ValidationError
import pandas as pd
import numpy as np
import base64
from io import BytesIO

# UPGRADES: 
# Can details be modified on the fly? or should user have to load the thing again

# UPGRADES views: ui prettier
# make a subcomponent for file card


# Extra addon: ANother addons for the enterprise version that accepts odoo spreadsheets

class ReconcileHistory(models.Model):
    _name = 'reconcile.history'
    _description = 'Reconcile History'

    name = fields.Char(string='Reconciliation Name', required=True)
    fileone = fields.Binary(string='File One', required=True)
    fileone_label = fields.Char(string='File One Label', required=True)
    filetwo = fields.Binary(string='File Two', required=True)
    filetwo_label = fields.Char(string='File Two Label', required=True)
    # Add these fields to view
    net = fields.Boolean(string="Net if balances add or substract", default=True)
    df1_initial_balance = fields.Float(string="Initial balance for first file")
    df2_initial_balance = fields.Float(string="Initial balance for second file")

    result = fields.Boolean(string="Reconciled", required=False)
    difference = fields.Float(string="Difference between statements", readonly=True)

    day_details = fields.One2many('reconcile.day', 'reconciliation_id', string="Day Details", readonly=True)
    details = fields.One2many('reconcile.details', 'reconciliation_id', string="Details", readonly=True)
    details_two = fields.One2many('reconcile.details', 'reconciliation_id_two', string="Details", readonly=True)

    def match_day_records(self):
        matched_details_one = self.day_details.filtered_domain([('match', '=', True), ('status', '=', 'bad')])
        matched_details_one.write({'status': 'ok'})

        self.env['ir.config_parameter'].sudo().set_param(
            f'user.{self.env.uid}.matched_details', "")



    def match_records(self):

        matched_details_one = self.details.filtered_domain([('match', '=', True), ('status', '=', 'bad')])
        matched_details_two = self.details_two.filtered_domain([('match', '=', True), ('status', '=', 'bad')])

        if matched_details_one and matched_details_two:
            matched_details_one.write({'status': 'ok'})
            matched_details_two.write({'status': 'ok'})

        # # Sum both matched details
        # total_matched_one = sum(matched_details_one.mapped('amount'))
        # total_matched_two = sum(matched_details_two.mapped('amount'))
        # if self.net:
        #     total_matched = total_matched_one + total_matched_two
        # else:
        #     total_matched = total_matched_one - total_matched_two

        # if round(total_matched, 2) != 0.00:
        #     raise ValidationError("Selected transactions do not match")
        # else:
        #     matched_details_one.write({'status': 'ok'})
        #     matched_details_two.write({'status': 'ok'})


        # self.env['ir.config_parameter'].sudo().set_param(
        #     f'user.{self.env.uid}.matched_details', "")

    @api.model
    def create(self, vals):
        new_record =super(ReconcileHistory, self).create(vals)
        try:
            new_record.reconcile_statements()
        except ValueError as e:
            raise ValidationError("Your loaded files do not fit the required format please load them again")
        except TypeError as e:
            raise ValidationError("Your files do not have the required data types load them again")


        return new_record


    def _validate_dataframe(self, df: pd.DataFrame, name: str):
        required_schema = {
            'date': 'datetime64[ns]',
            'amount': 'float',
            'memo': 'object',
            'transaction_id': 'object'
        }
        missing_cols = [col for col in required_schema if col not in df.columns]
        if missing_cols:
            raise ValueError(f"{name} is missing required columns: {missing_cols}")

        if len(df) < 1:
            raise ValueError("Your dataframe has no rows")

        # Check column types
        for col, expected_type in required_schema.items():
            actual_type = str(df[col].dtype)
            if expected_type == 'datetime64[ns]' and not pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    df[col] = pd.to_datetime(df[col])
                except Exception as e:
                    raise TypeError(f"Column '{col}' in {name} must be datetime64, but got {actual_type}")
            elif expected_type == 'float' and not pd.api.types.is_float_dtype(df[col]):
                try:
                    df[col] = df[col].astype(float)
                except Exception as e:
                    raise TypeError(f"Column '{col}' in {name} must be float, but got {actual_type}")
            elif expected_type == 'object' and not pd.api.types.is_object_dtype(df[col]):
                try:
                    df[col] = df[col].astype(object)
                except Exception as e:
                    raise TypeError(f"Column '{col}' in {name} must be string, but got {actual_type}")


    def reconcile_statements(self):
        columns = ['transaction_id', 'date', 'amount', 'memo']
        df1 = pd.read_excel(BytesIO(base64.b64decode(self.fileone)))
        df2 = pd.read_excel(BytesIO(base64.b64decode(self.filetwo)))
        df1 = df1[columns]
        df2 = df2[columns]

        self._validate_dataframe(df1, "file1")
        self._validate_dataframe(df2, "file2")

        df1['indexx'] = df1.index
        df2['indexx'] = df2.index

        # id, memo, amount, date, index

        # Checks if reconcile and sets the difference variables and the initial balances
        self._check_reconcile(df1, df2)

        if not self.result:
            df_day = self._calculate_day_differences(df1, df2)
            df_final = self._date_differences(df1, df2)
            self.update_details_table(df_final, df_day)
        
        else:
            self.delete_details_table()

    # This function is to check if the two provided statements reconcile or dont
    def _check_reconcile(self, df1, df2):
        total1 = df1['amount'].sum() + self.df1_initial_balance
        total2 = df2['amount'].sum() + self.df2_initial_balance

        if self.net:
            self.difference = round(total1, 2) + round(total2, 2)
        else:
            self.difference = round(total1, 2) - round(total2, 2)

        if abs(self.difference) > 0.5:
            self.result = False
        else:
            self.result = True


    def _calculate_day_differences(self, df1, df2):

        df1_grouped = df1.groupby('date')['amount'].sum().reset_index(name='amount_df1')
        df2_grouped = df2.groupby('date')['amount'].sum().reset_index(name='amount_df2')

        number_rows_grouped = len(df1_grouped)
        number_rows_grouped2 = len(df2_grouped)

        assert number_rows_grouped > 1
        assert number_rows_grouped2 > 1

        merged = pd.merge(df1_grouped, df2_grouped, on='date', how='outer').fillna(0)
        if self.net:
            merged['difference'] = merged['amount_df1'] + merged['amount_df2']
        else:
            merged['difference'] = merged['amount_df1'] - merged['amount_df2']

        merged['status'] = np.where(merged['difference'].round(2) == 0, 'ok', 'bad')

        assert max(number_rows_grouped, number_rows_grouped2) <= len(merged)

        return merged

        
    # Check for differences that can be netted
    def _date_differences(self, df1, df2):
        number_rows = len(df1)
        number_rows_two = len(df2)
        if self.net:
            df2['amount_original'] = df2['amount']
            df2['amount'] = -df2['amount']

        merged_df = df1.merge(df2[['date', 'amount', 'indexx']], on=["date", "amount"], how='outer', indicator=True)

        left_only = merged_df[merged_df['_merge'] == 'left_only']
        left_only['status'] = 'bad'
        left_only = left_only.rename(columns={'indexx_x': 'indexx'})
        left_only = left_only[['indexx', 'status']]
        df1 = df1.merge(left_only, on='indexx', how='left').fillna({'status': 'ok'})


        right_only = merged_df[merged_df['_merge'] == 'right_only']
        right_only['status'] = 'bad'
        right_only = right_only.rename(columns={'indexx_y': 'indexx'})
        right_only = right_only[['indexx', 'status']]
        df2 = df2.merge(right_only, on='indexx', how='left').fillna({'status': 'ok'})

        # Check transactions that are duplicate
        columns_duplicate = ['date', 'amount']
        duplicates = merged_df[merged_df.duplicated(columns_duplicate)][columns_duplicate].drop_duplicates(keep='first')
        count_df1 = df1.groupby(columns_duplicate)['indexx'].count().reset_index(name="count_x")
        count_df2 = df2.groupby(columns_duplicate)['indexx'].count().reset_index(name="count_y")
        duplicates = duplicates.merge(count_df1, on=columns_duplicate, how='left')
        duplicates = duplicates.merge(count_df2, on=columns_duplicate, how='left')
        duplicates['difference'] = duplicates['count_x'] - duplicates['count_y']
        bad_transactions = duplicates[abs(duplicates['difference']) > 0]

        for _, row in bad_transactions.iterrows():
            if row['difference'] > 0:
                bad_records = df1[(df1['date'] == row['date']) & (df1['amount'] == row['amount'])]
                bad_indices = bad_records.index[:abs(int(row['difference']))]
                df1.loc[bad_indices, 'status'] = 'bad'
            else:
                bad_records = df2[(df2['date'] == row['date']) & (df2['amount'] == row['amount'])]
                bad_indices = bad_records.index[:abs(int(row['difference']))]
                df2.loc[bad_indices, 'status'] = 'bad'

        assert number_rows == len(df1)
        assert number_rows_two == len(df2)

        if self.net:
            df2 = df2.drop('amount', axis=1)
            df2 = df2.rename(columns={'amount_original': 'amount'})

        df1['file'] = 'one'
        df1['reconciliation_id'] = self.id
        df1['reconciliation_id_two'] = False

        df2['file'] = 'two'
        df2['reconciliation_id'] = False
        df2['reconciliation_id_two'] = self.id

        df_final = pd.concat([df1, df2])

        return df_final

    def update_details_table(self, df_final, df_day):
        self.env['reconcile.day'].search([('reconciliation_id', '=', self.id)]).unlink()
        self.env['reconcile.details'].search([('reconciliation_id', '=', self.id)]).unlink()
        self.env['reconcile.details'].search([('reconciliation_id_two', '=', self.id)]).unlink()

        df_day['reconciliation_id'] = self.id

        df_final = df_final.drop('indexx', axis=1)

        self.env['reconcile.day'].create(df_day.to_dict(orient='records'))
        self.env['reconcile.details'].create(df_final.to_dict(orient='records'))

        
    def delete_details_table(self):
        self.env['reconcile.day'].search([('reconciliation_id', '=', self.id)]).unlink()
        self.env['reconcile.details'].search([('reconciliation_id', '=', self.id)]).unlink()
        self.env['reconcile.details'].search([('reconciliation_id_two', '=', self.id)]).unlink()

class ReconcileDay(models.Model):
    _name = "reconcile.day"
    _description = "Details of the reconciliation per day"

    reconciliation_id = fields.Many2one('reconcile.history', required=True, readonly=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True, readonly=True)
    amount_df1 = fields.Float(string="Total Amount file one", required=True, readonly=True)
    amount_df2 = fields.Float(string="Total Amount file two", required=True, readonly=True)
    difference = fields.Float(string="Difference", required=True, readonly=True)
    status = fields.Selection(selection=[('ok', '✅'), ('bad', '⚠️')], string='Status of Day', required=True, default='bad', readonly=True)
    match = fields.Boolean(default=False, store=False, readonly=True, compute="_compute_match_day")

    def _transform_list_val(self, parameter:str):
        list = parameter.split(",")
        return list

    def _compute_match_day(self):
        for record in self:
            val = self.env['ir.config_parameter'].sudo().get_param(
                f'user.{self.env.uid}.matched_day_details')

            if val == False:
                record.match = False
            else:
                val = self._transform_list_val(val)

                if str(record.id) in val:
                    record.match = True
                else:
                    record.match = False
        
    def set_match_true(self):
        for record in self:
            val = self.env['ir.config_parameter'].sudo().get_param(
                f'user.{self.env.uid}.matched_day_details')

            if record.match:
                if val == False:
                    final_param = ""
                else:
                    val = self._transform_list_val(val)
                    val.remove(str(record.id))
                    final_param = ",".join(val)
            else:
                if val == False:
                    final_param = str(record.id)
                else: 
                    val = self._transform_list_val(val)
                    val.append(str(record.id))
                    final_param = ",".join(val)

            self.env['ir.config_parameter'].sudo().set_param(
                f'user.{self.env.uid}.matched_day_details', final_param)





class ReconcileDetails(models.Model):
    _name = "reconcile.details"
    _description = "Details of the reconciliation"
    reconciliation_id = fields.Many2one('reconcile.history', readonly=True, ondelete='cascade')
    reconciliation_id_two = fields.Many2one('reconcile.history', readonly=True, ondelete='cascade')
    file = fields.Selection(selection=[('one', 'One'), ('two', 'Two')], string="File", required=True, readonly=True)
    date = fields.Date(string='Date', required=True, readonly=True)
    amount = fields.Float(string="Amount", required=True, readonly=True)
    memo = fields.Char(string="Memo", required=True, readonly=True)
    transaction_id = fields.Char(string="Transaction Id", readonly=True)
    partner = fields.Char(string="Partner", readonly=True)
    status = fields.Selection(selection=[('ok', '✅'), ('bad', '⚠️')], string='Status', required=True, default='bad', readonly=True)
    match = fields.Boolean(default=False, store=False, readonly=True, compute="_compute_match")




    def _transform_list_val(self, parameter:str):
        list = parameter.split(",")
        return list


    def _compute_match(self):
        for record in self:
            val = self.env['ir.config_parameter'].sudo().get_param(
                f'user.{self.env.uid}.matched_details')

            if val == False:
                record.match = False
            else:
                val = self._transform_list_val(val)

                if str(record.id) in val:
                    record.match = True
                else:
                    record.match = False
            

    def set_match_true(self):
        for record in self:
            val = self.env['ir.config_parameter'].sudo().get_param(
                f'user.{self.env.uid}.matched_details')

            if record.match:
                if val == False:
                    final_param = ""
                else:
                    val = self._transform_list_val(val)
                    val.remove(str(record.id))
                    final_param = ",".join(val)
            else:
                if val == False:
                    final_param = str(record.id)
                else: 
                    val = self._transform_list_val(val)
                    val.append(str(record.id))
                    final_param = ",".join(val)

            self.env['ir.config_parameter'].sudo().set_param(
                f'user.{self.env.uid}.matched_details', final_param)