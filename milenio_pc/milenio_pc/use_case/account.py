import frappe

def add_index(doc=None, method=None):
    frappe.db.add_index("GL Entry", ["party_type", "party"])
    frappe.db.add_index("GL Entry", ["is_cancelled"])
    frappe.db.add_index("Journal Entry Account", ["party_type", "party"])
    frappe.db.add_index("Journal Entry Account", ["party"])
    frappe.db.add_index("Journal Entry Account", ["reference_name"])
    frappe.db.add_index("Journal Entry Account", ["parent", "parentfield", "parenttype"])

    frappe.db.add_index("GL Entry", ["cost_center"])
    frappe.db.add_index("GL Entry", ["fiscal_year"])
    frappe.db.add_index("GL Entry", ["finance_book"])
    frappe.db.add_index("GL Entry", ["docstatus"])
    frappe.db.add_index("GL Entry", ["account", "party_type", "party"])

    frappe.db.add_index("Journal Entry Account", ["account", "party_type", "party"])
    frappe.db.add_index("Journal Entry Account", ["reference_type", "reference_name"])

    frappe.db.add_index("DocType Link", ["parent", "parentfield", "parenttype"])
