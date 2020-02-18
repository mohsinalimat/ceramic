import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, cstr, getdate

def check_sub(string, sub_str): 
    if (string.find(sub_str) == -1): 
       return False 
    else: 
        return True

def naming_series_name(name, company_series):
    
    if check_sub(name, '.fiscal.'):
        current_fiscal = frappe.db.get_value('Global Defaults', None, 'current_fiscal_year')
        fiscal = frappe.db.get_value("Fiscal Year", str(current_fiscal),'fiscal')
        name = name.replace('.fiscal.', str(fiscal))

    if check_sub(name, '.YYYY.'):
        name = name.replace('.YYYY.', '.2020.')

    if company_series:
        if check_sub(name, 'company_series.'):
            name = name.replace('company_series.', str(company_series))
            
    if check_sub(name, ".#"):
        name = name.replace('#', '')
        if name[-1] == '.':
            name = name[:-1]
    
    return name

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
def check_counter_series(name = None, company_series = None):
    name = naming_series_name(name, company_series)
    
    check = frappe.db.get_value('Series', name, 'current', order_by="name")
    
    if check == 0:
        return 1
    elif check == None:
        frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
        return 1
    else:
        return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1


@frappe.whitelist()
def before_naming(self, test):
    if not self.amended_from:
        if self.series_value:
            if self.series_value > 0:
                name = naming_series_name(self.naming_series, self.company_series)
                
                check = frappe.db.get_value('Series', name, 'current', order_by="name")
                if check == 0:
                    pass
                elif not check:
                    frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
                
                frappe.db.sql(f"update `tabSeries` set current = {int(self.series_value) - 1} where name = '{name}'")
        
@frappe.whitelist()
def get_party_details(party=None, party_type=None, ignore_permissions=True):

	if not party:
		return {}

	if not frappe.db.exists(party_type, party):
		frappe.throw(_("{0}: {1} does not exists").format(party_type, party))

	return _get_party_details(party, party_type, ignore_permissions)

def _get_party_details(party=None, party_type=None, ignore_permissions=True):

	out = frappe._dict({
		party_type.lower(): party
	})

	party = out[party_type.lower()]

	# if not ignore_permissions and not frappe.has_permission(party_type, "read", party):
	# 	frappe.throw(_("Not permitted for {0}").format(party), frappe.PermissionError)

	party = frappe.get_doc(party_type, party)
	
	# set_address_details(out, party, party_type)
	# set_contact_details(out, party, party_type)
	# set_other_values(out, party, party_type)
	set_organization_details(out, party, party_type)
	return out
		
def set_organization_details(out, party, party_type):

	organization = None

	if party_type == 'Lead':
		organization = frappe.db.get_value("Lead", {"name": party.name}, "company_name")
	elif party_type == 'Customer':
		organization = frappe.db.get_value("Customer", {"name": party.name}, "customer_name")
	elif party_type == 'Supplier':
		organization = frappe.db.get_value("Supplier", {"name": party.name}, "supplier_name")

	out.update({'party_name': organization})