import frappe
from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
from erpnext.stock.doctype.batch.batch import get_batch_qty
from frappe.utils import flt

def set_batch_nos(doc, warehouse_field, throw=False):
	"""Automatically select `batch_no` for outgoing items in item table"""
	for d in doc.items:
		qty = d.get('stock_qty') or d.get('transfer_qty') or d.get('qty') or 0
		has_batch_no = frappe.db.get_value('Item', d.item_code, 'has_batch_no')
		warehouse = d.get(warehouse_field, None)
		if has_batch_no and warehouse and qty > 0:
			if d.remove_batch:
				# frappe.throw("test")
				d.batch_no = None
				frppa.throw(f"Row: {i.idx} Please add batch no for item {d.item_code}")
			else:
				batch_qty = get_batch_qty(batch_no=d.batch_no, warehouse=warehouse)
				if flt(batch_qty, d.precision("qty")) < flt(qty, d.precision("qty")):
					frappe.throw(_("Row #{0}: The batch {1} has only {2} qty. Please select another batch which has {3} qty available or split the row into multiple rows, to deliver/issue from multiple batches").format(d.idx, d.batch_no, batch_qty, qty))


def validate(self):
	self.validate_posting_time()

	for i in self.items:
		i.remove_batch = False
		if not i.batch_no:
			i.remove_batch = True
	
	super(DeliveryNote, self).validate()
	self.set_status()
	self.so_required()
	self.validate_proj_cust()
	self.check_sales_order_on_hold_or_close("against_sales_order")
	self.validate_warehouse()
	self.validate_uom_is_integer("stock_uom", "stock_qty")
	self.validate_uom_is_integer("uom", "qty")
	self.validate_with_previous_doc()

	if self._action != 'submit' and not self.is_return:
		set_batch_nos(self, 'warehouse', True)

	from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
	make_packing_list(self)

	self.update_current_stock()

	if not self.installation_status: self.installation_status = 'Not Installed'