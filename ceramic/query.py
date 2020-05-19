import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from six import string_types
import json


def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
	cond = ""

	meta = frappe.get_meta("Batch")
	searchfield = meta.get_search_fields()

	searchfields = " or ".join(["batch." + field + " like %(txt)s" for field in searchfield])

	if filters.get("posting_date"):
		cond = "and (batch.expiry_date is null or batch.expiry_date >= %(posting_date)s)"
		
	if filters.get("customer"):
		cond = "and (batch.customer = %(customer)s or ifnull(batch.customer, '') = '') "

	batch_nos = None
	args = {
		'item_code': filters.get("item_code"),
		'warehouse': filters.get("warehouse"),
		'posting_date': filters.get('posting_date'),
		'txt': "%{0}%".format(txt),
		"start": start,
		"page_len": page_len
	}

	if args.get('warehouse'):
		batch_nos = frappe.db.sql("""select sle.batch_no, batch.lot_no, batch.packing_type, round(sum(sle.actual_qty),2), sle.stock_uom
				from `tabStock Ledger Entry` sle
				    INNER JOIN `tabBatch` batch on sle.batch_no = batch.name
				where
					sle.item_code = %(item_code)s
					and sle.warehouse = %(warehouse)s
					and batch.docstatus < 2
					and (sle.batch_no like %(txt)s or {searchfields})
					{0}
					{match_conditions}
				group by batch_no having sum(sle.actual_qty) > 0
				order by batch.expiry_date, sle.batch_no desc
				limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype), searchfields=searchfields), args)

	if batch_nos:
		return batch_nos
	else:
		return frappe.db.sql("""select batch.name, batch.lot_no, batch.packing_type, batch.expiry_date, sle.batch_no, batch.lot_no, round(sum(sle.actual_qty),2), sle.stock_uom from `tabBatch` batch
			JOIN `tabStock Ledger Entry` sle on sle.batch_no = batch.name
			where batch.item = %(item_code)s
			and batch.docstatus < 2
			and (sle.batch_no like %(txt)s or {searchfields})
			{0}
			{match_conditions} AND
			sle.company = '{company}'
			group by sle.batch_no having sum(sle.actual_qty) > 0
			order by batch.expiry_date, batch.name desc
			limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype), company=filters.get('company'), searchfields=searchfields), args)

def set_batches(self, warehouse_field):
	if self._action == 'submit':
		for row in self.items:
			if not row.get(warehouse_field):
				continue

			has_batch_no = frappe.db.get_value('Item', row.item_code, 'has_batch_no')
			
			if has_batch_no:
				if not row.get('lot_no'):
					frappe.throw(_("Please set Lot No in row {}".format(row.idx)))

				batch_no = get_batch(row.as_dict())

				if batch_no:
					row.batch_no = batch_no

			elif row.lot_no:
				frappe.throw(_("Please clear Lot No for Item {} as it is not batch wise item in row {}".format(row.item_code, row.idx)))

@frappe.whitelist()
def get_batch(args):
	"""
	Returns the batch according to Item Code, Merge and Grade
		args = {
			"item_code": "",
			"lot_no": "",
		}
	"""
	def process_args(args):
		if isinstance(args, string_types):
			args = json.loads(args)

		args = frappe._dict(args)
		return args

	def validate_args(args):
		if not args.item_code:
			frappe.throw(_("Please specify Item Code"))

		elif not args.lot_no:
			frappe.throw(_("Please specify Lot NO"))

	args = process_args(args)

	validate_args(args)

	batch_nos = frappe.db.sql_list(""" select name from `tabBatch` 
		where lot_no = %s and item = %s """, (args.lot_no, args.item_code))

	batch_no = None
	if batch_nos:
		batch_no = batch_nos[0]

	return batch_no
			

# def get_batch_no(doctype, txt, searchfield, start, page_len, filters):
# 	cond = ""

# 	meta = frappe.get_meta("Batch")
# 	searchfield = meta.get_search_fields()

# 	searchfields = " or ".join(["batch." + field + " like %(txt)s" for field in searchfield])

# 	if filters.get("posting_date"):
# 		cond = "and (batch.expiry_date is null or batch.expiry_date >= %(posting_date)s)"

# 	batch_nos = None
# 	args = {
# 		'item_code': filters.get("item_code"),
# 		'warehouse': filters.get("warehouse"),
# 		'posting_date': filters.get('posting_date'),
# 		'customer':  filters.get('customer'),
# 		'txt': "%{0}%".format(txt),
# 		"start": start,
# 		"page_len": page_len
# 	}

# 	if args.get('warehouse'):
# 		batch_nos = frappe.db.sql("""select sle.batch_no, batch.lot_no, batch.packing_type, round(sum(sle.actual_qty),2), sle.stock_uom
# 				from `tabStock Ledger Entry` sle
# 				    INNER JOIN `tabBatch` batch on sle.batch_no = batch.name
# 				where
# 					sle.item_code = %(item_code)s
# 					and sle.warehouse = %(warehouse)s
# 					and batch.docstatus < 2
# 					and (sle.batch_no like %(txt)s or {searchfields})
# 					{0}
# 					{match_conditions}
# 				group by batch_no having sum(sle.actual_qty) > 0
# 				order by batch.expiry_date, sle.batch_no desc
# 				limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype), searchfields=searchfields), args)
# 		return batch_nos
# 	else:
		# return frappe.db.sql("""select batch.name, batch.lot_no, batch.packing_type, batch.expiry_date, sle.batch_no, batch.lot_no, round(sum(sle.actual_qty),2), sle.stock_uom from `tabBatch` batch
		# 	JOIN `tabStock Ledger Entry` sle on sle.batch_no = batch.name
		# 	where batch.item = %(item_code)s
		# 	and batch.docstatus < 2
		# 	and (sle.batch_no like %(txt)s or {searchfields})
		# 	{0}
		# 	{match_conditions} AND
		# 	sle.company = '{company}'
		# 	group by sle.batch_no having sum(sle.actual_qty) > 0
		# 	order by batch.expiry_date, batch.name desc
		# 	limit %(start)s, %(page_len)s""".format(cond, match_conditions=get_match_cond(doctype), company=filters.get('company'), searchfields=searchfields), args)