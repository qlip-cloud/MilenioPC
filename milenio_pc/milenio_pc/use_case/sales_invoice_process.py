import json
import frappe
from frappe.utils import flt
from datetime import datetime
from frappe.utils import add_to_date, getdate, now, get_time
from erpnext.stock.get_item_details import get_item_tax_info
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.accounts.doctype.payment_entry.payment_entry import get_reference_details
#from erpnext.regional.india.e_invoice.utils import make_einvoice

def sales_invoice_orchestrator(doc):

    data_temp_loaded = frappe.db.sql(f'SELECT * FROM tabMilenio_Temporal_Data_File WHERE temporal_lot = "{doc.name}" ORDER BY doc_number ASC', as_dict=1)
    doctype_data = None
    data_temp_loaded_len = len(data_temp_loaded) - 1

    price_list, price_list_currency = frappe.db.get_values("Price List", {"selling": 1}, ['name', 'currency'])[0]

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
            doc_item_tax = frappe.get_last_doc("Item Tax", filters={"parent":doc_item.name, "item_tax_template":['like', f'%{row.iva_tax} %']})
        except frappe.exceptions.DoesNotExistError as exc_iva_tax:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Plantilla de impuesto {row.iva_tax} no existe para producto {doc_item.name} - {exc_iva_tax}"

        try:
            doc_item_tax_temp = frappe.get_last_doc("Item Tax Template", filters={"name":doc_item_tax.item_tax_template, "company":doc.company})
        except frappe.exceptions.DoesNotExistError as exc_iva:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Plantilla de impuesto no existe - {doc_item_tax.item_tax_template} - {exc_iva}"

        try:
            doc_sales_person = frappe.get_doc("Sales Person", row.seller_nit)
        except frappe.exceptions.DoesNotExistError as exc_sales_person:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Alguna persona de venta no existe - {row.seller_nit} - {exc_sales_person}"
        
        try:
            
            kwargs = {
                "doc":doc,
                "row":row,
                "item":doc_item,
                "item_tax":doc_item_tax_temp,
                "customer":doc_customer,
                "account":doc_account,
                "price_list":price_list,
                "price_list_currency":price_list_currency,
                "sales_person":doc_sales_person
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
                
                frappe.flags.in_import = True
                
                sales_invoice_doc = frappe.get_doc(doctype_data)
                #sales_invoice_doc = make_einvoice(sales_invoice_doc)
                sales_invoice_doc.set_missing_values(True)
                cal_taxes_and_totals(sales_invoice_doc)
                sales_invoice_doc.insert()

                frappe.flags.in_import = False
               
        except frappe.exceptions.DuplicateEntryError as sa_in_du:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Algun secuencial de factura se repite - {row.naming_series}{row.doc_number} - {sa_in_du}"
        except frappe.exceptions.UniqueValidationError as sa_in_uni:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Algun valor requerido se encuentra vacio - {row.naming_series}{row.doc_number} - {sa_in_uni}"
        except Exception as sa_in_exc:
            frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
            frappe.db.rollback()
            return True, f"Archivo con error - {row.naming_series}{row.doc_number} - {sa_in_exc}"

    frappe.db.commit()
    return False, None

def new_invoice(doc, row, item, item_tax, customer, account, price_list, price_list_currency, sales_person):

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
            'posting_date': getdate(datetime.strptime(row.doc_date.split(" ")[0], "%d/%m/%Y")),
            'posting_time': get_time(row.doc_date),
            'due_date':add_to_date(datetime.now(), days=int(row.exp_date), as_string=True),
            'items':[],
            "status":"Draft",
            "taxes_and_charges": customer.sales_item_tax_template,
            "taxes":[],
            'selling_price_list': price_list,
            'price_list_currency': price_list_currency,
            'plc_conversion_rate': 1.0,
            'sales_team':[{
                'sales_person':sales_person.name,
                'allocated_percentage':100.00
            }]
        }

def new_item_invoice(doc, row, item, item_tax, customer, account, price_list, price_list_currency, sales_person):

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
                "base_amount": qty * row.unit_price,
                "net_amount": qty * row.unit_price,
                "base_net_amount": qty * row.unit_price,
                "unit_price": row.unit_price
            }

def cal_taxes_and_totals(doc):

    cruzar_impuestos = 0

    try:
        cruzar_impuestos = frappe.db.get_single_value('Dynamic Taxes Config', "cruzar_impuestos")
    except Exception as e:
        pass

    for item in doc.items:
        item.item_tax_template = item.item_tax_template
        add_taxes_from_item_tax_template(item, doc, cruzar_impuestos)

    if doc.taxes_and_charges:

        taxes = get_taxes_and_charges('Sales Taxes and Charges Template', doc.taxes_and_charges)

        for tax in taxes:
            
            if cruzar_impuestos:

                flag_add_tax = True

                if not any((item_tax.get("account_head") == tax.get("account_head") and item_tax.get("rate") == tax.get("rate")) for item_tax in doc.taxes):
                    for item in doc.items:
                       
                        if frappe.db.exists("Item Tax Template Detail", {"parent":item.item_tax_template, "tax_type":tax.get("account_head"), "tax_rate":tax.get("rate")}):
                            
                            if tax.charge_type in ['On Previous Row Amount', 'Previous Row Total'] and cruzar_impuestos:
                                
                                prev_account_head = taxes[int(tax.row_id) -1].account_head
                                prev_rate = taxes[int(tax.row_id) -1].rate

                                ex = False

                                for item_temp in doc.items:
                                    if frappe.db.exists("Item Tax Template Detail", {"parent":item_temp.item_tax_template, "tax_type":prev_account_head, "tax_rate":prev_rate}):
                                        ex = True

                                if not ex:
                                    flag_add_tax = False

                            if flag_add_tax:

                                if tax.charge_type in ['On Previous Row Amount', 'Previous Row Total']:

                                    if cruzar_impuestos:
                                         tax.row_id = doc.taxes[-1:][0].idx
                                    else:
                                        tax.row_id = tax.row_id

                                doc.append('taxes', tax)
            else:
                if not any(item_tax.get("account_head") == tax.get("account_head") for item_tax in doc.taxes):
                    doc.append('taxes', tax)

    doc.calculate_taxes_and_totals()

def add_taxes_from_item_tax_template(child_item, parent_doc, cruzar_impuestos):
    
    add_taxes_from_item_tax_template = frappe.db.get_single_value("Accounts Settings", "add_taxes_from_item_tax_template")

    if child_item.item_tax_rate and add_taxes_from_item_tax_template:

        tax_map = json.loads(child_item.item_tax_rate)

        for tax_type in tax_map:

            tax_rate = flt(tax_map[tax_type])
            taxes = parent_doc.taxes or []
            # add new row for tax head only if missing
            if cruzar_impuestos:

                found = any((tax.account_head == tax_type and tax.rate == tax_rate) for tax in taxes)

                exist = frappe.db.exists("Sales Taxes and Charges", {"parent": parent_doc.taxes_and_charges, "account_head":tax_type, "rate":tax_rate})

                if not exist and not found:
                    found = True

            else:
                found = any((tax.account_head == tax_type and tax.rate == tax_rate) for tax in taxes)

            if not found:
                
                flag_add_tax = True

                charge_type, row_id = frappe.db.get_value("Sales Taxes and Charges", {"parent": parent_doc.taxes_and_charges, "account_head":tax_type, "rate":tax_rate}, ['charge_type', 'row_id'])

                tax_detail = {
                    "description" : str(tax_type).split(' - ')[0],
                    "charge_type" : charge_type if cruzar_impuestos else "On Net Total",
                    "account_head" : tax_type,
                    "rate" : tax_rate if cruzar_impuestos else 0
                }

                if charge_type in ['On Previous Row Amount', 'Previous Row Total'] and cruzar_impuestos:

                    account_head, rate = frappe.db.get_value("Sales Taxes and Charges", {"parent": parent_doc.taxes_and_charges, "idx":row_id}, ['account_head', 'rate'])
                    
                    ex = False

                    for tax_type in tax_map:
                        if account_head == tax_type and flt(rate) == flt(tax_map[tax_type]):
                            ex = True
                    
                    if not ex:
                        flag_add_tax = False
            
                if flag_add_tax:
                    if charge_type in ['On Previous Row Amount', 'Previous Row Total']:
                        tax_detail.update({"row_id": parent_doc.taxes[-1:][0].idx}) if cruzar_impuestos else tax_detail.update({"row_id": row_id})

                    parent_doc.append("taxes", tax_detail)