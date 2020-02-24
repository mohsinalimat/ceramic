import frappe
from frappe import _
from frappe.utils import flt, cint, cstr
import datetime

def stock_entry_on_sumbit(self,metod):
	if self.stock_entry_type == "Material Receipt":
		make_batches(self, 't_warehouse')

def stock_entry_on_cancel(self, method):
	if self.stock_entry_type == "Material Receipt":
		delete_batches(self, 't_warehouse')

def pr_on_submit(self,method):
	make_batches(self, 'warehouse')

def pr_on_cancel(self, method):
	delete_batches(self, 'warehouse')

def make_batches(self, warehouse_field):
	if self._action == "submit":
		for row in self.items:
			if not row.get(warehouse_field):
				continue

			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			if has_batch_no:
				batch = frappe.new_doc("Batch")
				batch.item = row.item_code
				batch.supplier = getattr(self, 'supplier', None)
				batch.lot_no = cstr(row.lot_no)
				batch.packaging_material = cstr(row.packaging_material)
				batch.valuation_rate = flt(row.valuation_rate, 4)
				batch.posting_date = datetime.datetime.strptime(self.posting_date, "%Y-%m-%d").strftime("%y%m%d")
				batch.actual_quantity = flt(row.qty * row.conversion_factor)
				batch.reference_doctype = self.doctype
				batch.reference_name = self.name
				batch.insert()

				if row.batch_no and self.doctype == "Stock Entry":
					row.db_set('old_batch_no', row.batch_no)
				
				row.batch_no = batch.name

def delete_batches(self, warehouse):
	from frappe.model.delete_doc import check_if_doc_is_linked
	for row in self.items:
		if row.batch_no and row.get(warehouse):
			batch_no = frappe.get_doc("Batch", row.batch_no)
			frappe.msgprint(str(batch_no.name))
			# frappe.db.set_value("Batch", batch_no.name, 'reference_doctype','')
			# frappe.db.set_value("Batch", batch_no.name, 'reference_name','')
			# frappe.db.set_value("Stock Entry Detail", row.name, 'batch_no','')
			# frappe.db.set_value("Stock Entry Detail", row.name, 'old_batch_no','')
			batch_no.db_set('reference_doctype','')
			batch_no.db_set('reference_name','')
			# batch_no.reference_doctype = ''
			# batch_no. = ''
			# row.batch_no = ''
			check_if_doc_is_linked(batch_no)
			row.db_set('batch_no', '')
			
			frappe.delete_doc("Batch", batch_no.name)
			
	else:
		frappe.db.commit()