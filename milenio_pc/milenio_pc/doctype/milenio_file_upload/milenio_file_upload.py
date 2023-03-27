# Copyright (c) 2023, Henderson Villegas and contributors
# For license information, please see license.txt

import os
import frappe
from frappe import _
from frappe.model.document import Document
from milenio_pc.milenio_pc.use_case.milenio_file_import import milenio_file_import

class Milenio_File_Upload(Document):

	def validate(self):

		if not self.import_file:
			frappe.throw(_("Please attach file to import"))

		root, extension = os.path.splitext(self.import_file)

		if extension != ".txt":
			frappe.throw(_("Allowed extension .txt"))

		if not self.company:
			frappe.throw(_("Please select company"))

	@frappe.whitelist()
	def do_import_file(self):
		try:
			result_import = self.do_import()
			return True

		except Exception as error:
			frappe.log_error(message=frappe.get_traceback(), title="do_import_file")
			pass

		return False

	def do_import(self):

		# Validar que haya un adjunto
		if not self.import_file or not self.company:
			frappe.throw(_("Please attach file to import or select company"))

		# Validar la extensión del archivo
		root, extension = os.path.splitext(self.import_file)

		if extension != ".txt":
			frappe.throw(_("Allowed extension .txt"))

		if self.status == 'Active':
			frappe.throw(_("Job already running to upload."))

		# validar procesos simultáneos
		simultaneous_process = frappe.db.sql("""
				Select count(*)
				from tabMilenio_File_Upload
				WHERE status = 'Active'""")[0][0] or 0

		if simultaneous_process != 0:
			frappe.throw(_("Other job of File Import already running."))
		
		self.status = 'Active'
		self.save(ignore_permissions=True)
		self.reload()

		frappe.enqueue(milenio_file_import, doc=self, is_async=True, timeout=54000)

		return
