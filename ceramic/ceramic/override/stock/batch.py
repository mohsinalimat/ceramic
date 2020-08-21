import frappe

@frappe.whitelist()
def get_batch_no(item_code, warehouse, qty=1, throw=False, serial_no=None):
	"""
	Get batch number using First Expiring First Out method.
	:param item_code: `item_code` of Item Document
	:param warehouse: name of Warehouse to check
	:param qty: quantity of Items
	:return: String represent batch number of batch with sufficient quantity else an empty String
	"""

	batch_no = None
	# batches = get_batches(item_code, warehouse, qty, throw, serial_no)

	# for batch in batches:
	# 	if cint(qty) <= cint(batch.qty):
	# 		batch_no = batch.batch_id
	# 		break

	# if not batch_no:
		# frappe.msgprint(_('Please select a Batch for Item {0}. Unable to find a single batch that fulfills this requirement').format(frappe.bold(item_code)))
		# if throw:
		# 	raise UnableToSelectBatchError
		# pass

	return batch_no