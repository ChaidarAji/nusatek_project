# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    customer_invoice_signature = fields.Char(
        string="Customer Invoice Signature"
    )
