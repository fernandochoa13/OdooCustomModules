# -*- coding: utf-8 -*-

import json
from odoo import http, fields
from odoo.http import request


class CRMLeadController(http.Controller):

    @http.route('/api/lead/save', auth='api_key', type='http', csrf=False, methods=['POST'])
    def lead_save(self):
        request_data = request.httprequest.data
        if not request_data:
            return http.Response(json.dumps({
                "status": "error",
                "message": "No data provided"
            }), status=400, content_type="application/json")
        data = json.loads(request_data)

        if not data.get("client"):
            return http.Response(json.dumps({
                "status": "error",
                "message": "No data provided for client"
            }), status=400, content_type="application/json")

        if not data['client'].get('name'):
            return http.Response(json.dumps({
                "status": "error",
                "message": "No name provided for client"
            }), status=400, content_type="application/json")

        last_name = (' %s' % data['client']['last_name']) if data['client'].get('last_name') else ''
        lead = request.env['crm.lead'].sudo().create({
            "name": f"{data['client']['name']}{last_name}",
            "email_from": data["client"]["email"],
            "phone": data["client"]["phone"],
            "zip": data["client"]["zipcode"],
            "street": data["client"]["address"]
        })

        # TODO: Save lead data
        return http.Response(json.dumps({
            "status": "success",
            "message": "Lead created successfully",
            "lead_id": lead.id,
            "data": data,
        }), status=200, content_type="application/json")
