import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc


def before_save(self, method):
    """On Submit Custom Function for Sales Invoice"""
    create_warehouse(self)


def create_warehouse(self):
    if self.company:

        # Getting authority of company
        authority = frappe.db.get_value("Company", self.company, "authority")

        if authority == "Authorized":
            target_company = frappe.db.get_value("Company", self.company, "alternate_company")
            
            w = frappe.new_doc("Warehouse")

            w.warehouse_name = self.warehouse_name
            w.company = frappe.db.get_value("Company", self.company, "alternate_company")

            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", self.company, "abbr")

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
            

            