import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.model.rename_doc import rename_doc


def before_save(self, method):
    """On Submit Custom Function for Sales Invoice"""
    create_warehouse(self)

def before_rename(self, method, old, new, merge = False):
    authority = frappe.db.get_value("Company", self.company, "authority")

    if authority == 'Authorized':
        target_company = frappe.db.get_value("Company", self.company, "alternate_company")
        
        target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
        source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")

        w_old = old.replace(source_company_abbr, target_company_abbr)
        w_new = new.replace(source_company_abbr, target_company_abbr)
        
        if frappe.db.exists("Warehouse", w_old):
            rename_doc("Warehouse", w_old, w_new, merge=merge)

def create_warehouse(self):
    if self.company:

        # Getting authority of company
        authority = frappe.db.get_value("Company", self.company, "authority")

        if authority == "Authorized":
            target_company = frappe.db.get_value("Company", self.company, "alternate_company")
            
            if frappe.db.exists("Warehouse", {"company": target_company, "warehouse_name": self.warehouse_name}):
                w = frappe.get_doc("Warehouse", {"company": target_company, "warehouse_name": self.warehouse_name})
            else:
                w = frappe.new_doc("Warehouse")

            w.warehouse_name = self.warehouse_name
            w.company = frappe.db.get_value("Company", self.company, "alternate_company")

            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")
    
            if self.is_group:
                w.is_group = self.is_group
            
            if self.parent_warehouse:
                w.parent_warehouse = self.parent_warehouse.replace(source_company_abbr, target_company_abbr)
            
            if self.account:
                w.account = self.account.replace(source_company_abbr, target_company_abbr)
            
            if self.disabled:
                w.disabled = s.disabled

            try:
                w.save()
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)
            