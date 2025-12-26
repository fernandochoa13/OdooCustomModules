# -*- coding: utf-8 -*-
from odoo import models, fields, api


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    plus_property_images_id = fields.Many2one(
        comodel_name="plus.properties",
        string="Property images",
        required=False
    )
    plus_property_views_id = fields.Many2one(
        comodel_name="plus.properties",
        string="Property views",
        required=False
    )
    plus_property_marketing_id = fields.Many2one(
        comodel_name="plus.properties",
        string="Property marketing",
        required=False
    )
    plus_property_legal_id = fields.Many2one(
        comodel_name="plus.properties",
        string="Property legal",
        required=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for value in vals_list:
            property_id = (
                value.get("plus_property_images_id") or
                value.get("plus_property_views_id") or
                value.get("plus_property_marketing_id") or
                value.get("plus_property_legal_id")
            )
            if property_id:
                value["res_model"] = "plus.properties"
                value["res_id"] = property_id
        res = super(IrAttachment, self).create(vals_list)
        return res

    @api.model
    def check(self, mode, values=None):
        if self and mode == "read":
            uid = self.env.context.get("uid", False)
            user_can_access = False
            if uid:
                user = self.env["res.users"].browse(uid)
                if user and (user.has_group("base.group_public") or user.has_group("base.group_portal")):
                    user_can_access = True
            else:
                user_can_access = True
            if user_can_access:
                # SQL: If we use the self.filtered, the check method is called more than once.
                self.env['ir.attachment'].flush_model(['res_model', 'res_id', 'create_uid', 'public', 'res_field'])
                self._cr.execute(
                    'SELECT res_model, res_id, create_uid, public, res_field FROM ir_attachment WHERE id IN %s',
                    [tuple(self.ids)])
                for res_model, res_id, create_uid, public, res_field in self._cr.fetchall():
                    if res_model == 'plus.properties':
                        return True
        return super(IrAttachment, self).check(mode, values=values)
