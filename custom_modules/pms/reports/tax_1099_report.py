from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, UserError

class tax1099report(models.Model):
    _name = "tax.tenninetynine.report"
    _description = "1099 report"
    _auto = False

    id = fields.Integer(readonly=True)
    date = fields.Date(readonly=True, string="Date")
    company = fields.Many2one("res.company", readonly=True, string="Company")
    name = fields.Char(readonly=True, string="Label")
    journal_entry = fields.Many2one("account.move", readonly=True, string="Journal Entry")
    account = fields.Many2one("account.account", readonly=True)
    paid_with = fields.Many2one("account.account", readonly=True)
    vendor = fields.Many2one("res.partner", readonly=True)
    vendor_address = fields.Char(readonly=True)
    vendor_tax_id = fields.Char(readonly=True)
    type_1099 = fields.Many2one('l10n_us.1099_box', readonly=True)
    amount = fields.Float(readonly=True)

    @property
    def _table_query(self):
        pct = "%"
        query = f"""
                    select aml.id as id, max(aml.date) as date, max(aml.company_id) as company, max(aml.account_id) as account,
                    max(aml.partner_id) as vendor, max(aml.balance) as amount, max(aml.move_id) as journal_entry, max(aml.name) as name,
                    max(paml.paid_with) as paid_with, max(res_partner.vat) as vendor_tax_id, max(res_partner.contact_address_complete) as vendor_address,
                    max(res_partner.box_1099_id) as type_1099

                    from account_move_line aml
                    inner join res_partner on aml.partner_id = res_partner.id
                    inner join account_account on aml.account_id = account_account.id
                    inner join (
                        select account_move_line.move_id as paid_move_id, account_move_line.account_id as paid_with 
                        from account_move_line

                        inner join account_account on account_move_line.account_id = account_account.id 


                        where (((account_account.account_type = 'liability_credit_card' or account_account.account_type = 'asset_cash' or account_account.name ilike '%%outstanding%%' or
                          account_account.code = '2000401' or (account_account.account_type = 'liability_payable' and account_move_line.matching_number is not null))
                          and account_move_line.credit > 0) or (account_account.code = '6000027' and account_move_line.debit > 0)) and account_move_line.parent_state = 'posted'
                         ) paml on aml.move_id = paml.paid_move_id

                    where res_partner.box_1099_id is not null and (account_account.internal_group = 'expense' or account_account.code = '1000201' or account_account.code = '1815202')
                          and aml.parent_state = 'posted'
                    group by aml.id
                    
        """
        return query 
 


