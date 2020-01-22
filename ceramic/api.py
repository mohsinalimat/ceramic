import frappe
from frappe import _

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
        name = name.replace('.2020.')

    if company_series:
        if check_sub(name, '.company_series.'):
            name = name.replace('.company_series.', str(company_series))
    
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
    if check <= 0:
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