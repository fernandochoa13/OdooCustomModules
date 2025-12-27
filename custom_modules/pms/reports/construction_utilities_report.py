from odoo import models, fields, tools
    
####################################################################################################################################################################################################################################################################################

# TABLA PRINCIPAL CONSTRUCTION_UTILITIES_REPORT

class construction_utilities_report(models.Model):
    _name = "pms.construction.utilities.report"
    _description = "Construction Utilities Report"
    _auto = False
    
    # GENERAL PROPERTY FIELDS
    id = fields.Integer(readonly=True)
    county_id = fields.Many2one('pms.county', string="County", readonly=True)
    address_id = fields.Many2one('pms.property', string="Address", readonly=True)
    superintendent_id = fields.Many2one('hr.employee', string="Superintendent", readonly=True)
    construction_status = fields.Char(string="Construction Status", readonly=True)
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)
    
    # ELECTRICAL UTILITIES
    
    # WATER UTILITIES
    
    # SEWAGE UTILITIES
    
    
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'pms_construction_utilities_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW pms_construction_utilities_report AS (
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