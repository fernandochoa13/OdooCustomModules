from odoo import api, models, fields


class pms_housemodels(models.Model):
    _name = "pms.housemodels"
    _description = "Models of Houses"

    # === General Property Description === #
    name = fields.Char(string="Name of House Model")
    floor = fields.Many2one("pms.floors", string="Floor")
    roof = fields.Many2one("pms.roof", string="Roof")
    windows = fields.Many2one("pms.windows", string="Windows")
    budget_model = fields.Many2one("crossovered.budget", string="Model Budget")
