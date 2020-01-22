import frappe
from frappe import _

def check_sub(string, sub_str): 
    if (string.find(sub_str) == -1): 
       return False 
    else: 
        return True

@frappe.whitelist()
def docs_before_naming(self, method):
	from erpnext.accounts.utils import get_fiscal_year

	date = self.get("transaction_date") or self.get("posting_date") or getdate()

	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	if fiscal:
		self.fiscal = fiscal
	else:
		fy_years = fy.split("-")
		fiscal = fy_years[0][2:] + "-" + fy_years[1][2:]
		self.fiscal = fiscal

@frappe.whitelist()
def check_counter_series(name = None):
	pass