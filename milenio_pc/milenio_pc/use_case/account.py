import frappe

def add_index(doc=None, method=None):
    frappe.db.add_index("GL Entry", ["party_type", "party"])
    frappe.db.add_index("Journal Entry Account", ["party_type", "party"])
