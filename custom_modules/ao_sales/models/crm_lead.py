# -*- coding: utf-8 -*-

from odoo import models, fields


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    city_of_interest_construction = fields.Selection(
        [
            ('port_fl', 'Port Charlotte FL'),
            ('ocala_fl', 'Ocala FL'),
            ('sebring_fl', 'Sebring Fl'),
            ('advice', 'I want advice on these 3 areas')
        ],
        string='City of Interest for Construction? (Old field)'
    )
    city_of_interest_advice = fields.Char(string='City of Interest for Construction?')
    pre_approved = fields.Selection(
        [
            ('yes', 'Yes, I already know the price range I qualify for'),
            ('no', 'No, I need help')
        ],
        string='Pre-Approved?'
    )
    interest = fields.Selection(
        [
            ('build', 'Build'),
            ('buy', 'Buy finished houses'),
            ('acquire', 'Acquire lands in Florida'),
            ('invest', 'Invest passively with ADAN'),
            ('invest_real', 'Passively investing in real estate')
        ],
        string='Interest?'
    )
    has_capital = fields.Selection(
        [
            ('yes', 'Yes, I have the capital or I am pre-approved'),
            ('have_10', 'I have between 10k and 25k saved to invest'),
            ('no', "I don't have much saved")
        ],
        string='Has Capital?'
    )
    city_of_interest = fields.Char(string="City of interest")

    def save_answer_by_lang(
            self, lang, question, answer, map_questions_fields, optional_not_selection_fields, map_answers):
        if map_questions_fields[lang][question] in optional_not_selection_fields:
            self.write({
                map_questions_fields[lang][question]: str(answer)
            })
        else:
            str_answer = str(answer)
            if str_answer in map_answers[lang]:
                self.write({
                    map_questions_fields[lang][question]: map_answers[lang][str_answer]
                })

    def save_appointment_answers(self, map_questions_fields, optional_not_selection_fields, map_answers):
        for lead in self:
            if not lead.description:
                continue

            # Get all <li> lines except first two
            questions_answers = [line.split('</li>')[0].strip() for line in lead.description.split('<li>')[1:]][2:]

            for qa in questions_answers:
                split_qa = qa.split(":")
                # Build question and answer
                question = split_qa[0] + ":" + split_qa[1] if len(split_qa) > 2 else split_qa[0]
                answer = str(split_qa[-1].strip()).replace("&nbsp;", "")

                # If the question is mapped, then save on its field
                if question in map_questions_fields["ES"]:
                    lead.save_answer_by_lang(
                        "ES", question, answer, map_questions_fields, optional_not_selection_fields, map_answers)
                elif question in map_questions_fields["EN"]:
                    lead.save_answer_by_lang(
                        "EN", question, answer, map_questions_fields, optional_not_selection_fields, map_answers)
