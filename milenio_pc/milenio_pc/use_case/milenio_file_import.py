import frappe
from frappe import _

from frappe.utils import now, make_esc
from milenio_pc.milenio_pc.use_case.sales_invoice_process import sales_invoice_orchestrator
import os


def milenio_file_import(doc):
	
	process_start_date = now()
	error = False
	message = ''

	try:
		
		#SE LIMPIAN LOS REGISTROS EXISTENTES PARA LA CARGA ACTUAL
		clear_temporal_data_rows(doc)

		#SE CARGAN LOS REGISTROS DEL ARCHIVO A LA TABLA TEMPORAL
		load_return = load_data_infile_to_temporal(doc)

		if not load_return == 0:
			error = True
			message = "File upload failed. Check the format or content used for the upload."

		#SE VERIFICA QUE SE HAYAN CARGADO LOS REGISTROS
		verify_return = verify_temporal_load_data(doc)

		if not verify_return > 0:
			error = True
			message = "Rows not loaded."

		clients_not_exists = verify_all_clients(doc)

		if clients_not_exists:
			error = True
			message = "\n".join(clients_not_exists)

		if not error:
			#SE EJECUTA PROCESO PARA VALIDACION Y CARGA DE FACTURAS
			try:
				error, message = sales_invoice_orchestrator(doc)
				if message:
					message = f"Error creando facturas - {message}"
			except Exception as soo_exc:
				error = True
				message = f"Error creando facturas - {soo_exc}"
				frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")

	except Exception as exc:
		error = True
		frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
		pass

	finally:

		try:

			doc.append('import_list', {
					"status": "Failed" if error else "Completed",
					"start_date": process_start_date,
					"result_message": message if message != "" else "Some error has occurred, check the log.",
					"finish_date": now()
				})
			doc.status = "Failed" if error else "Completed"
			doc.save(ignore_permissions=True)

		except Exception as exce:
			frappe.log_error(message=frappe.get_traceback(), title="milenio_file_import")
			pass
	
	return

def clear_temporal_data_rows(doc):
	#SE LIMPIAN LOS REGISTROS DEL TEMPORAL PARA EL ID ESPECIFICO
	frappe.db.sql(f"DELETE FROM `tabMilenio_Temporal_Data_File` WHERE temporal_lot = '{doc.name}'", as_dict=1)
	frappe.db.commit()

def load_data_infile_to_temporal(doc):

	esc = make_esc('$ ')
	db_user = frappe.conf.db_name
	db_pass = frappe.conf.db_password
	db_name = frappe.conf.db_name

	#SE BUSCAN LAS RUTAS DEL ARCHIVO
	abs_site_path = os.path.abspath(frappe.get_site_path())
	file_path = ''.join((abs_site_path, doc.import_file))

	#SE ESTRUCTURAN LAS VARIABLE DE COMANDO

	db_port = f'-P{frappe.db.port}' if frappe.db.port else ''
	db_host = esc(frappe.db.host)

	#SE REALIZA LA CARGA DE DATOS DESDE EL ARCHIVO A LA TEMPORAL A TRAVEZ DE COMMAND LINE
	load_qry = f"""<<EOF
SET @a:=0;
LOAD DATA LOCAL INFILE '{file_path}' 
INTO TABLE tabMilenio_Temporal_Data_File
CHARACTER SET latin1
FIELDS TERMINATED BY ', ' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY "\\n\\r\\n"
(doc_type, doc_number, naming_series, item_num, item_quantity, unit_price, iva_tax, total, account, client_nit, client_name, doc_date, observation, item_code, item_desc, exp_date, doc_status, discount_percent, discount_value, seller_nit)
SET name = CONCAT('{doc.name}_', @a:=@a+1),
temporal_lot = '{doc.name}',
company = '{doc.company}';
EOF"""

	load_command_line = f"""mysql -h {db_host} {db_port} -u {db_user} -p{db_pass} -D {db_name} {load_qry}"""	
	load = os.system(load_command_line)

	return load

def verify_temporal_load_data(doc):

	count = frappe.db.sql(f"SELECT COUNT(*) AS count FROM `tabMilenio_Temporal_Data_File` WHERE temporal_lot = '{doc.name}'", as_dict=1)[0].count
	return count


def verify_all_clients(doc):

	clients_not_exists = []

	rows = frappe.db.sql(f"SELECT client_nit, client_name FROM `tabMilenio_Temporal_Data_File` WHERE temporal_lot = '{doc.name}'", as_dict=1)

	for row in rows:
		if not frappe.db.sql(f"SELECT 1 FROM tabCustomer WHERE tax_id = {row.client_nit} AND sales_item_tax_template is not NULL"):
			clients_not_exists.append(f'Cliente {row.client_nit} - {row.client_name} no existe, no ha sido creado o no contiene plantilla de impuesto asociada.')

	return clients_not_exists
