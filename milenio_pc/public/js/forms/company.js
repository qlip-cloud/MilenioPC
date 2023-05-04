frappe.ui.form.on("Company", "refresh", function(frm) {
    frm.add_custom_button(__("Milenio Advanced Integration"), function() {
        frappe.set_route("List", "milenio_file_upload");
    });
});