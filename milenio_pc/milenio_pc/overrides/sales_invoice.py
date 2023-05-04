import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from frappe.model.naming import parse_naming_series
# from milenio_pc.controllers.customer_naming import set_new_name

class CustomSalesInvoice(SalesInvoice):

	def autoname(self):
		name = self.naming_series + self.sequence
		parts = name.split('.')
		self.name = parse_naming_series(parts)  