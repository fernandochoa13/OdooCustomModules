# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Document(models.Model):
    _inherit = 'documents.document'

    plus_property_id = fields.Many2one(
        comodel_name="plus.properties",
        string="Property",
        required=False
    )

    def get_field_name_by_folder(self):
        return {
            record["folder"].id: record["field_name"]
            for record in [
                {
                    "folder": self.env.ref(
                        "ao_properties.documents_properties_pictures_folder", raise_if_not_found=False),
                    "field_name": "plus_property_images_id",
                },
                {
                    "folder": self.env.ref(
                        "ao_properties.documents_properties_views_folder", raise_if_not_found=False),
                    "field_name": "plus_property_views_id",
                },
                {
                    "folder": self.env.ref(
                        "ao_properties.documents_properties_marketing_folder", raise_if_not_found=False),
                    "field_name": "plus_property_marketing_id",
                },
                {
                    "folder": self.env.ref("ao_properties.documents_properties_legal_folder", raise_if_not_found=False),
                    "field_name": "plus_property_legal_id",
                }
            ]
        }

    @api.model_create_multi
    def create(self, vals_list):
        documents = super(Document, self).create(vals_list)
        for document in documents:
            if document.attachment_id and document.attachment_id.res_model == "plus.properties":
                document.write({
                    "plus_property_id": int(document.attachment_id.res_id),
                })

                field_name = self.get_field_name_by_folder().get(document.folder_id.id, False)
                if field_name:
                    document.attachment_id.write({
                        field_name: int(document.attachment_id.res_id),
                    })
        return documents
