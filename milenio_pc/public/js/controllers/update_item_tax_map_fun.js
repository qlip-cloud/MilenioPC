// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

erpnext.taxes_and_totals.prototype.update_item_tax_map = function() {

		let me = this;
		let item_codes = [];
		let item_rates = {};
        let item_tax_templates = {};
		$.each(this.frm.doc.items || [], function(i, item) {
			if (item.item_code) {
				// Use combination of name and item code in case same item is added multiple times
				item_codes.push([item.item_code, item.name]);
				item_rates[item.name] = item.net_rate;
                item_tax_templates[item.item_code] = item.item_tax_template;
			}
		});

		if (item_codes.length) {
			return this.frm.call({
				method: "erpnext.stock.get_item_details.get_item_tax_info",
				args: {
					company: me.frm.doc.company,
					tax_category: cstr(me.frm.doc.tax_category),
					item_codes: item_codes,
					item_rates: item_rates,
                    item_tax_templates: Object.keys(item_tax_templates).length ? item_tax_templates : null
				},
				callback: function(r) {
					if (!r.exc) {
						$.each(me.frm.doc.items || [], function(i, item) {
							if (item.name && r.message.hasOwnProperty(item.name)) {
								item.item_tax_template = r.message[item.name].item_tax_template;
								item.item_tax_rate = r.message[item.name].item_tax_rate;
								me.add_taxes_from_item_tax_template(item.item_tax_rate);
							} else {
								item.item_tax_template = "";
								item.item_tax_rate = "{}";
							}
						});
					}
				}
			});
		}
	}