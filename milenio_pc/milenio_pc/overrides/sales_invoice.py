import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.model.naming import parse_naming_series
# from milenio_pc.controllers.customer_naming import set_new_name

class CustomSalesInvoice(SalesInvoice):

	def autoname(self):
		name = self.naming_series + self.sequence
		parts = name.split('.')
		self.name = parse_naming_series(parts)  

	def calculate_taxes_and_totals(self):

		from .custom_calculate_taxes_and_totals import custom_calculate_taxes_and_totals

		custom_calculate_taxes_and_totals(self)

		if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
			self.calculate_commission()
			self.calculate_contribution()