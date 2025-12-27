from odoo import api, models, tools, fields

class inspections_general_report(models.Model):
    _name = "pms.inspections.general.report"
    _description = "Inspections General Report"
    _auto = False
    
    # filter fields
    own_third_property = fields.Selection(readonly=True, selection=[("own", "Own"), ("third", "Third Party")])
    status_construction = fields.Selection(string="Construction Status", readonly=True, selection=[
        ("pending", "Pending"), ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"), ("pip", "PIP"), 
        ("pps", "PPS"), ("ppa", "PPA"), ("cop", "COP"), ("cop1", "COP1"), ("cop2", "COP2"), 
        ("cop3", "COP3"), ("cop4", "COP4"), ("cop5", "COP5"), ("coc", "COC"), ("completed", "Completed")])
    
    # Ambos campos de projects routes lines
    # add_to_report = fields.Boolean(string="Add to Report", readonly=True)
    # activity_type
    
    # report fields
    
    address_id = fields.Many2one('pms.property', string="Address", readonly=True)
    e_conn_status = fields.Selection(string="Electrical Connection Status", readonly=True,
        selection=[('disconnected', "Disconnected"), ('connected', "Connected")])
    w_conn_status = fields.Selection(string="Electrical Connection Status", readonly=True,
        selection=[('disconnected', "Disconnected"), ('connected', "Connected")])
    issued_date = fields.Date(string="Issued Date", readonly=True)
    expiration_date = fields.Date(string="Expiration Date", readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self._cr, 'pms_inspections_general_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW pms_inspections_general_report AS (
                SELECT
                    pj.id AS id,
                    pj.own_third_property AS own_third_property,
                    pj.status_construction AS status_construction,
                    pj.issued_date AS issued_date,
                    pj.expiration_date AS expiration_date,
                    pp.address AS address_id,
                    pp.e_conn_status AS e_conn_status,
                    pp.w_conn_status AS w_conn_status
                FROM pms_projects pj
                LEFT JOIN pms_property pp ON pp.id = pj.address
            )
        """)