from datetime import datetime
from frappe.utils import add_to_date, getdate, now
import frappe

def sales_invoice_orchestrator(doc):

    data_temp_loaded = frappe.db.sql(f'SELECT * FROM tabMilenio_Temporal_Data_File WHERE temporal_lot = "{doc.name}" ORDER BY doc_number ASC', as_dict=1)
    doctype_data = None
    data_temp_loaded_len = len(data_temp_loaded) - 1

    for index, row in enumerate(data_temp_loaded):

        try:
            doc_customer = frappe.get_doc("Customer", row.client_nit)
        except frappe.exceptions.DoesNotExistError as exc_cus:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Algun cliente no existe."

        try:
            doc_item = frappe.get_doc("Item", row.item_code)
        except frappe.exceptions.DoesNotExistError as exc_item:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Algun producto no existe."

        try:
            doc_account = frappe.get_last_doc("Account", filters={"account_number":row.account, "company":doc.company})
        except frappe.exceptions.DoesNotExistError as exc_acco:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Cuenta de ingreso no existe."

        try:
            doc_item_tax = frappe.get_last_doc("Item Tax Template", filters={"title":row.iva_tax,"company":doc.company})
        except frappe.exceptions.DoesNotExistError as exc_iva:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Plantilla de impuesto no existe."

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
                print(doctype_data)
                sales_invoice_doc = frappe.get_doc(doctype_data)
                sales_invoice_doc.insert(sales_invoice_doc)         

        except frappe.exceptions.DuplicateEntryError as sa_in_du:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Algun secuencial de factura se repite."
        except frappe.exceptions.UniqueValidationError as sa_in_uni:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Algun valor requerido se encuentra vacio."
        except Exception as sa_in_exc:
            print(sa_in_exc)
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, "Archivo con error."

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
            }
