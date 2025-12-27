from odoo import api, models, fields, tools
    
####################################################################################################################################################################################################################################################################################

# TABLA PRINCIPAL PURCHASES GENERAL REPORT

class purchases_general_report(models.Model):
    _name = "pms.purchases.general.report"
    _description = "Purchases General Report"
    _auto = False
    
    # id = fields.Integer(readonly=True)
    # county = fields.Char(readonly=True)
    # address = fields.Char(readonly=True)
    # house_model = fields.Char(readonly=True)
    # state_ids = fields.Char(readonly=True)
    # status_property = fields.Char(readonly=True)
    # order_type = fields.Char(readonly=True)
    # date_approved = fields.Datetime(readonly=True)
    # date_planned = fields.Datetime(readonly=True)
    # effective_date = fields.Datetime(readonly=True)
    # receipt_status = fields.Char(readonly=True)

    # date_order = fields.Datetime(readonly=True)
    # product_category = fields.Char(readonly=True)
    # product = fields.Char(readonly=True)
    # vendor = fields.Char(readonly=True)
    # quantity = fields.Float(readonly=True)
    # price_unit = fields.Float(readonly=True)
    # total_amount = fields.Float(readonly=True, group_operator = "avg")
    # ref = fields.Char(readonly=True)

    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""
    #                         CREATE OR REPLACE VIEW %s AS (
    #                             SELECT 
    #                             purchase_order_line.id as id, 
    #                             pms_property.name AS address, 
    #                             pms_property.status_property AS status_property, 
    #                             purchase_order_line.product_qty as quantity,
    #                             purchase_order_line.price_unit as price_unit, 
    #                             purchase_order_line.price_total as total_amount, 
    #                             purchase_order.date_order as date_order, 
    #                             res_partner.name as vendor, 
    #                             purchase_order.name as ref,
    #                             product as product, 
    #                             product_category.complete_name as product_category, 
    #                             pms_county.name AS county, 
    #                             res_country_state.name AS state_ids, 
    #                             pms_housemodels.name AS house_model,
    #                             purchase_order.order_type as order_type, 
    #                             purchase_order.date_approve as date_approved, 
    #                             purchase_order.date_planned as date_planned, 
    #                             purchase_order.effective_date as effective_date, 
    #                             purchase_order.receipt_status as receipt_status

    #                         FROM pms_property

    #                         INNER JOIN (SELECT id, purchase_order_line.order_id, purchase_order_line.product_id, purchase_order_line.product_qty, purchase_order_line.price_unit, purchase_order_line.price_total, CAST(jsonb_object_keys(analytic_distribution) AS INTEGER) AS analytic_key
    #                         FROM purchase_order_line)
    #                         purchase_order_line ON pms_property.analytical_account =  purchase_order_line.analytic_key

    #                         INNER JOIN purchase_order ON purchase_order_line.order_id = purchase_order.id

    #                         LEFT JOIN product_product ON purchase_order_line.product_id = product_product.id

    #                         LEFT JOIN (SELECT id, categ_id, name ->>'en_US' as product FROM product_template) 
    #                         product_template ON product_product.product_tmpl_id = product_template.id

    #                         LEFT JOIN product_category ON product_template.categ_id = product_category.id

    #                         LEFT JOIN pms_county ON pms_property.county = pms_county.id

    #                         LEFT JOIN res_country_state ON pms_property.state_ids = res_country_state.id

    #                         LEFT JOIN pms_housemodels ON pms_property.house_model = pms_housemodels.id

    #                         LEFT JOIN res_partner ON purchase_order.partner_id = res_partner.id
                            
    #                         WHERE purchase_order.state = 'purchase')
    #                         """ % (self._table))
    
    
    # GENERAL PROPERTY FIELDS
    id = fields.Integer(readonly=True)
    county_id = fields.Many2one('pms.county', string="County", readonly=True)
    address_id = fields.Many2one('pms.property', string="Address", readonly=True)
    superintendent_id = fields.Many2one('hr.employee', string="Superintendent", readonly=True)
    construction_status = fields.Char(string="Construction Status", readonly=True)
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)
    

    
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'pms_purchases_general_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW pms_purchases_general_report AS (
                SELECT                          
                    p.name AS id,
                    p.county AS county_id,
                    p.address AS address_id,
                    p.superintendent AS superintendent_id,
                    p.status_construction AS construction_status,
                    p.issued_date AS issued_date,
                    p.expiration_date AS expiration_date
                FROM pms_projects p
                LEFT JOIN pms_property ON pms_property.id = p.address
                WHERE pms_property.on_hold = FALSE AND p.superintendent IS NOT NULL AND p.visit_day IS NOT NULL
            )
        """)