# Copyright (c) 2023, Henderson Villegas and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

NAME = "Sales Invoice-naming_series-options"
PROPERTY_SETTER = "Property Setter"

class Milenio_Temporal_Data_File(Document):
	
	def validate(self):

		if self.naming_serie:
			naming_series = frappe.get_doc(PROPERTY_SETTER, NAME)

			if not naming_series:
				frappe.throw(_("Naming Series is not valid"))

			options = "\n".join(naming_series.value)

			try:
				options.index(self.naming_serie)
			except ValueError:
				frappe.throw(_("Naming Series is not valid"))


