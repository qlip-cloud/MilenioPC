import frappe
from frappe.utils import flt
from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

class custom_calculate_taxes_and_totals(calculate_taxes_and_totals):

    def _get_tax_rate(self, tax, item_tax_map):

        try:
            impuesto_individual = frappe.db.get_single_value('Dynamic Taxes Config', "impuesto_individual")
        except Exception as e:
            impuesto_individual = 0

        if tax.account_head in item_tax_map:
            return flt(item_tax_map.get(tax.account_head), self.doc.precision("rate", tax))
        else:
            if impuesto_individual:
                return 0
            else:
                return tax.rate