// Copyright (c) 2023, Henderson Villegas and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.toggle_enable(['sequence'], True);
		}
	}
});
