import frappe

def add_index(doc=None, method=None):
    frappe.db.add_index("GL Entry", ["party_type", "party"])
    frappe.db.add_index("GL Entry", ["is_cancelled"])
    frappe.db.add_index("Journal Entry Account", ["party_type", "party"])
    frappe.db.add_index("Journal Entry Account", ["party"])
    frappe.db.add_index("Journal Entry Account", ["reference_name"])
    frappe.db.add_index("Journal Entry Account", ["parent", "parentfield", "parenttype"])
