import frappe
from frappe import _
from frappe.model.naming import make_autoname
from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.batch.batch import Batch
from erpnext.stock.doctype.batch.batch import batch_uses_naming_series, get_name_from_hash

def get_fiscal(date):
	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	return fiscal if fiscal else fy.split("-")[0][2:] + fy.split("-")[1][2:]

def batch_before_name(self,method):
	Batch.autoname = override_batch_autoname

def override_batch_autoname(self):
	"""Generate random ID for batch if not specified"""
	if not self.batch_id:
		create_new_batch, batch_number_series = frappe.db.get_value('Item', self.item,
			['create_new_batch', 'batch_number_series'])

		if create_new_batch:
			if batch_number_series:
				self.batch_id = make_autoname(batch_number_series)
			elif batch_uses_naming_series():
				self.batch_id = Batch.get_name_from_naming_series(self)
			else:
				self.batch_id = get_name_from_hash()
		else:
			frappe.throw(_('Batch ID is mandatory'), frappe.MandatoryError)
	
	date = self.get("manufacturing_date") or getdate()
	fiscal = get_fiscal(date)
	
	self.batch_id = self.batch_id.replace('fiscal', fiscal)
	# frappe.throw(str(self.batch_id))
	self.name = self.batch_id
