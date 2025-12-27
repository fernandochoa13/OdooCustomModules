from odoo import api, models, tools, fields
from datetime import datetime, time, timedelta
from datetime import date
import base64
import io


class account_creditcard_usable(models.Model):
    _name = 'pms.purchase.report'
    _description = "Property Purchase Report"
    _auto = False

    id = fields.Integer(readonly=True)
    address = fields.Char(readonly=True)
    house_model = fields.Char(readonly=True)
    state_ids = fields.Char(readonly=True)
    county = fields.Char(readonly=True)
    status_property = fields.Char(readonly=True)
    order_type = fields.Char(readonly=True)
    date_approved = fields.Datetime(readonly=True)
    date_planned = fields.Datetime(readonly=True)
    effective_date = fields.Datetime(readonly=True)
    receipt_status = fields.Char(readonly=True)

    date_order = fields.Datetime(readonly=True)
    product_category = fields.Char(readonly=True)
    product = fields.Char(readonly=True)
    vendor = fields.Char(readonly=True)
    quantity = fields.Float(readonly=True)
    price_unit = fields.Float(readonly=True)
    total_amount = fields.Float(readonly=True, group_operator = "avg")
    ref = fields.Char(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
                            CREATE OR REPLACE VIEW %s AS (SELECT purchase_order_line.id as id, pms_property.name AS address, pms_property.status_property AS status_property, 
                            purchase_order_line.product_qty as quantity,
                            purchase_order_line.price_unit as price_unit, purchase_order_line.price_total as total_amount, purchase_order.date_order as date_order, res_partner.name as vendor, purchase_order.name as ref,
                            product as product, product_category.complete_name as product_category, pms_county.name AS county, res_country_state.name AS state_ids, pms_housemodels.name AS house_model,
                            purchase_order.order_type as order_type, purchase_order.date_approve as date_approved, purchase_order.date_planned as date_planned, purchase_order.effective_date as effective_date, purchase_order.receipt_status as receipt_status

                            FROM pms_property

                            INNER JOIN (SELECT id, purchase_order_line.order_id, purchase_order_line.product_id, purchase_order_line.product_qty, purchase_order_line.price_unit, purchase_order_line.price_total, CAST(jsonb_object_keys(analytic_distribution) AS INTEGER) AS analytic_key
                            FROM purchase_order_line)
                            purchase_order_line ON pms_property.analytical_account =  purchase_order_line.analytic_key

                            INNER JOIN purchase_order ON purchase_order_line.order_id = purchase_order.id

                            LEFT JOIN product_product ON purchase_order_line.product_id = product_product.id

                            LEFT JOIN (SELECT id, categ_id, name ->>'en_US' as product FROM product_template) 
                            product_template ON product_product.product_tmpl_id = product_template.id

                            LEFT JOIN product_category ON product_template.categ_id = product_category.id

                            LEFT JOIN pms_county ON pms_property.county = pms_county.id

                            LEFT JOIN res_country_state ON pms_property.state_ids = res_country_state.id

                            LEFT JOIN pms_housemodels ON pms_property.house_model = pms_housemodels.id

                            LEFT JOIN res_partner ON purchase_order.partner_id = res_partner.id
                            
                            WHERE purchase_order.state = 'purchase')
                            """ % (self._table))
        

    def print_materials_report(self):
        return self.env.ref('pms.report_purchase_pms_action').report_action(self)
    
    def _send_weekly_report_purchase(self):

        end_of_day = datetime.combine(datetime.now(), time.max)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=7)


        records = self.search(["|", "&",("effective_date", "<", end_of_day), ("effective_date", ">", start_of_day), "&", ("date_approved", ">", start_of_day), ("date_approved", "<", end_of_day)])

        lista_county = set(records.mapped("county"))

        for x in lista_county:
             
            county_filter = records.filtered(lambda r: r.county == x)

            data_record = base64.b64encode(self.env.ref("pms.report_purchase_pms_action").sudo()._render_qweb_pdf(self.env.ref("pms.report_purchase_pms_action").ids[0], county_filter.ids)[0])        
            ir_values = {
                    'name': f"{x}WeeklyPurchaseReports{date.today()}.pdf",
                    'type': 'binary',
                    'datas': data_record,
                    'store_fname': data_record
                    }
            data_id = self.env['ir.attachment'].create(ir_values)
                
            email_template = self.env.ref('pms.email_template_weekly_purchase_report')
            i = 0
            for record in self:
                    if i < 1:
                        email_template.attachment_ids = [(4, data_id.id)]
                        email_value={'subject': f'{x} Weekly Purchases Report'}
                        email_template.send_mail(record.id, email_values = email_value, force_send=True)
                        email_template.attachment_ids = [(5, 0, 0)]

                        i = i + 1
            else:
                pass

    def _send_daily_report_purchase(self):

        end_of_day = datetime.combine(datetime.now(), time.max) - timedelta(days=1)
        start_of_day = datetime.combine(datetime.now(), time.min) - timedelta(days=1)


        records = self.search(["|", "&",("effective_date", "<", end_of_day), ("effective_date", ">", start_of_day), "&", ("date_approved", ">", start_of_day), ("date_approved", "<", end_of_day)])

        lista_county = set(records.mapped("county"))

        for x in lista_county:
             
            county_filter = records.filtered(lambda r: r.county == x)

            data_record = base64.b64encode(self.env.ref("pms.report_purchase_pms_action").sudo()._render_qweb_pdf(self.env.ref("pms.report_purchase_pms_action").ids[0], county_filter.ids)[0])        
            ir_values = {
                    'name': f"{x}DailyPurchaseReports{date.today()}.pdf",
                    'type': 'binary',
                    'datas': data_record,
                    'store_fname': data_record
                    }
            data_id = self.env['ir.attachment'].create(ir_values)
                
            email_template = self.env.ref('pms.email_template_purchase_report_daily')
            i = 0
            for record in self:
                    if i < 1:
                        email_template.attachment_ids = [(4, data_id.id)]
                        email_value={'subject': f'{x} Daily Purchases Report'}
                        email_template.send_mail(record.id, email_values = email_value, force_send=True)
                        email_template.attachment_ids = [(5, 0, 0)]

                        i = i + 1
            else:
                pass
    

