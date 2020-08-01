import frappe
from frappe import _
from frappe.utils import flt, cint, cstr
import datetime

def stock_entry_on_sumbit(self,metod):
	if self.stock_entry_type == "Material Receipt":
		update_batch(self)

def pr_on_submit(self,method):
	update_batch(self)

def update_batch(self):
	if self._action == "submit":
		for row in self.items:
			if not row.get("batch_no"):
				continue

			batch = frappe.get_doc('Batch', row.batch_no)
			batch.item = row.item_code
			batch.supplier = getattr(self, 'supplier', None)
			batch.lot_no = row.lot_no
			batch.packing_type = row.packing_type
			# batch.posting_date = datetime.datetime.strptime(self.posting_date, "%Y-%m-%d").strftime("%y%m%d")
			batch.reference_doctype = ''
			batch.reference_name = ''
			batch.save(ignore_permissions=True)

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

def make_batches(self, warehouse_field):
	'''Create batches if required. Called before submit'''
	for d in self.items:
		if d.get(warehouse_field) and not d.batch_no:
			has_batch_no, create_new_batch = frappe.db.get_value('Item', d.item_code, ['has_batch_no', 'create_new_batch'])
			if has_batch_no and create_new_batch:
				if frappe.db.exists("Batch",{'item':d.item_code,'packing_type':d.packing_type,'lot_no':d.lot_no}):
					d.batch_no = frappe.db.get_value("Batch",{'item':d.item_code,'packing_type':d.packing_type,'lot_no':d.lot_no})
				else:
					d.batch_no = frappe.get_doc(dict(
						doctype='Batch',
						item=d.item_code,
						packing_type=d.packing_type,
						lot_no=d.lot_no,
						supplier=getattr(self, 'supplier', None)
					)).insert().name