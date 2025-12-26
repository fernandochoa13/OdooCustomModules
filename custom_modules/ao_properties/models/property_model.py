from odoo import fields, models


class PropertyModel(models.Model):
    _name = 'plus.property.model'
    _description = 'Property Model'

    name = fields.Char(string="Name")
    area = fields.Integer(string="Area")
    image = fields.Binary(string="Image")
    number_of_beds = fields.Integer(string="Number of Beds")
    number_of_baths = fields.Integer(string="Number of Baths")
    number_of_garages = fields.Integer(string="Number of Garages")
    description = fields.Char(string="Description")
