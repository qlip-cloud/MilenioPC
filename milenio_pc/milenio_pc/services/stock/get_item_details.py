import frappe
import json
from erpnext.stock.get_item_details import get_item_tax_template, get_item_tax_map
from six import string_types, iteritems

@frappe.whitelist()
def get_item_tax_info(company, tax_category, item_codes, item_rates=None, item_tax_templates=None):
	
	out = {}
	if isinstance(item_codes, string_types):
		item_codes = json.loads(item_codes)

	if isinstance(item_rates, string_types):
		item_rates = json.loads(item_rates)

	if isinstance(item_tax_templates, string_types):
		item_tax_templates = json.loads(item_tax_templates)

	for item_code in item_codes:
		if not item_code or item_code[1] in out:
			continue
		out[item_code[1]] = {}
		item = frappe.get_cached_doc("Item", item_code[0])

		args = {"company": company, "tax_category": tax_category, "net_rate": item_rates[item_code[1]]}
		
		if item_tax_templates:
			out[item_code[1]]["item_tax_rate"] = get_item_tax_map(company, item_tax_templates[item_code[0]], as_json=True)
			out[item_code[1]]["item_tax_template"] = item_tax_templates[item_code[0]]
		else:
			get_item_tax_template(args, item, out[item_code[1]])
			out[item_code[1]]["item_tax_rate"] = get_item_tax_map(company, out[item_code[1]].get("item_tax_template"), as_json=True)

	
	return out