import frappe
from datetime import datetime
from frappe.utils import add_to_date, getdate, now
from erpnext.stock.get_item_details import get_item_tax_info
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.accounts.doctype.payment_entry.payment_entry import get_reference_details

def sales_invoice_orchestrator(doc):

    data_temp_loaded = frappe.db.sql(f'SELECT * FROM tabMilenio_Temporal_Data_File WHERE temporal_lot = "{doc.name}" ORDER BY doc_number ASC', as_dict=1)
    doctype_data = None
    data_temp_loaded_len = len(data_temp_loaded) - 1

    for index, row in enumerate(data_temp_loaded):
        try:
            doc_customer = frappe.get_last_doc("Customer", filters={"tax_id":row.client_nit})
        except frappe.exceptions.DoesNotExistError as exc_cus:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Algun cliente no existe - {row.client_nit} - {exc_cus}"

        try:
            doc_item = frappe.get_doc("Item", row.item_code)
        except frappe.exceptions.DoesNotExistError as exc_item:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Algun producto no existe - {row.item_code} - {exc_item}"

        try:
            doc_account = frappe.get_last_doc("Account", filters={"account_number":row.account, "company":doc.company})
        except frappe.exceptions.DoesNotExistError as exc_acco:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Cuenta de ingreso no existe - {row.account} - {exc_acco}"

        try:
            doc_item_tax = frappe.get_last_doc("Item Tax Template", filters={"title":row.iva_tax,"company":doc.company})
        except frappe.exceptions.DoesNotExistError as exc_iva:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Plantilla de impuesto no existe - {row.iva_tax} - {exc_iva}"

        try:
            
            kwargs = {
                "doc":doc,
                "row":row,
                "item":doc_item,
                "item_tax":doc_item_tax,
                "customer":doc_customer,
                "account":doc_account
            }

            if index == 0:
                doctype_data = new_invoice(**kwargs)
                doctype_data["items"].append(new_item_invoice(**kwargs))
            elif  index > 0 and (data_temp_loaded[index - 1].doc_number != row.doc_number):
                doctype_data = new_invoice(**kwargs)
                doctype_data["items"].append(new_item_invoice(**kwargs))
            else:
                doctype_data["items"].append(new_item_invoice(**kwargs))

            if (index < data_temp_loaded_len and data_temp_loaded[index + 1].doc_number != row.doc_number) or index == data_temp_loaded_len:
                
                sales_invoice_doc = frappe.get_doc(doctype_data)

                cal_taxes_and_totals(sales_invoice_doc)

                sales_invoice_doc.insert(sales_invoice_doc)         

        except frappe.exceptions.DuplicateEntryError as sa_in_du:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Algun secuencial de factura se repite - {row.doc_number} - {sa_in_du}"
        except frappe.exceptions.UniqueValidationError as sa_in_uni:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Algun valor requerido se encuentra vacio - {row.doc_number} - {sa_in_uni}"
        except Exception as sa_in_exc:
            print(sa_in_exc)
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Archivo con error - {sa_in_exc}"

    frappe.db.commit()
    return False, None

def new_invoice(doc, row, item, item_tax, customer, account):

    return {
            'doctype': 'Sales Invoice',
            'sequence':row.doc_number,
            'is_return': True if row.doc_type == 'NC' else False,
            'company': doc.company,
            'customer': customer.name,
            'title': customer.customer_name,
            'naming_series':row.naming_series,
            'customer_name':customer.customer_name,
            'tax_id':customer.tax_id,
            'posting_date': getdate(row.doc_date),
            'due_date':add_to_date(datetime.now(), days=int(row.exp_date), as_string=True),
            'items':[],
            "status":"Draft"
        }

def new_item_invoice(doc, row, item, item_tax, customer, account):

    qty = (int(row.item_quantity) * -1) if row.doc_type == 'NC' else int(row.item_quantity)

    return {
                "item_code":item.name,
                "item_name":item.item_name,
                "uom":item.stock_uom,
                "description":item.item_name,
                "qty": qty,
                "stock_qty":qty,
                "stock_uom":item.stock_uom,
                "income_account": account.name,
                "item_tax_template":item_tax.name,
                "rate":row.unit_price,
                "base_rate":row.unit_price,
                "net_rate":row.unit_price,
                "base_net_rate":row.unit_price,
                "amount": qty * row.unit_price,
                "base_amount":qty * row.unit_price,
                "net_amount": qty * row.unit_price,
                "base_net_amount": qty * row.unit_price,
                "taxes_and_charges": customer.sales_item_tax_template
            }

def cal_taxes_and_totals(doc):

    item_codes = []
    item_rates = {}

    for item in doc.items:

        if item.item_code:
            item_codes.append([item.item_code, item.name])
            item_rates[item.name] = item.net_rate

        if len(item_codes):

            res_out = get_item_tax_info(doc.company, doc.tax_category, item_codes, item_rates)

            for item in doc.items:

                if item.name:
                    item.item_tax_template = res_out[item.name].item_tax_template
                    item.item_tax_rate = res_out[item.name].item_tax_rate
                    add_taxes_from_item_tax_template(item, doc)
                else:
                    item.item_tax_template = ""
                    item.item_tax_rate = ""

    if doc.taxes_and_charges:

        taxes = get_taxes_and_charges('Sales Taxes and Charges Template', doc.taxes_and_charges)

        for tax in taxes:
            doc.append('taxes', tax)

        doc.calculate_taxes_and_totals()

    def add_taxes_from_item_tax_template(child_item, parent_doc):

        add_taxes_from_item_tax_template = frappe.db.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template")

        if child_item.item_tax_rate and add_taxes_from_item_tax_template:
            tax_map = json.loads(child_item.item_tax_rate)
            for tax_type in tax_map:
                tax_rate = flt(tax_map[tax_type])
                taxes = parent_doc.taxes or []
                # add new row for tax head only if missing
                found = any(tax.account_head == tax_type for tax in taxes)
                if not found:
                    tax_row = parent_doc.append("taxes", {})
                    tax_row.update({
                        "description" : str(tax_type).split(' - ')[0],
                        "charge_type" : "On Net Total",
                        "account_head" : tax_type,
                        "rate" : 0
                    })
                    tax_row.db_insert()