import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc

def on_submit(self, test):
    """On Submit Custom Function for Sales Invoice"""
    create_main_sales_invoice(self)

def on_cancel(self, test):
    """On Cancel Custom Function for Sales Invoice"""
    cancel_main_sales_invoice(self)

def on_trash(self, test):
    delete_sales_invoice(self)

def change_delivery_authority(name):
    dn_status = frappe.get_value("Delivery Note", name, "status")
    if dn_status == 'Completed':
        frappe.db.set_value("Delivery Note",name, "authority", "Unauthorized")
    else:
        frappe.db.set_value("Delivery Note",name, "authority", "Authorized")
    
    frappe.db.commit()

# Create New Invouice on Submit
def create_main_sales_invoice(self):
    
    # Getting authority of company
    authority = frappe.db.get_value("Company", self.company, "authority")

    def get_sales_invoice_entry(source_name, target_doc=None, ignore_permissions= True):
        def set_target_values(source, target):
            target_company = frappe.db.get_value("Company", source.company, "alternate_company")
            target.company = target_company
            target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
            source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

            target.ref_invoice = self.name
            target.authority = "Unauthorized"

            if source.debit_to:
                target.debit_to = source.debit_to.replace(source_company_abbr, target_company_abbr)
            if source.taxes_and_charges:
                target.taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)

                for index, i in enumerate(source.taxes):
                    target.taxes[index].charge_type = "Actual"
                    target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)

            if self.amended_from:
                name = frappe.db.get_value("Sales Invoice", {"ref_invoice": source.amended_from}, "name")
                target.amended_from = name

            target.set_missing_values()

        def account_details(source_doc, target_doc, source_parent):
            target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

            doc = frappe.get_doc("Company", target_company)

            target_doc.income_account = doc.default_income_account
            target_doc.expense_account = doc.default_expense_account
            target_doc.cost_center = doc.cost_center

        fields = {
            "Sales Invoice": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "ref_invoice": "name",
                },
                "field_no_map":{
                    "authority",
                }
            },
            "Sales Invoice Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "item_design": "item_code",
                    "item_code": "item_design",
                    "full_rate": "rate",
                    "full_qty": "qty",
                    "rate": "discounted_rate",
                    "qty": "real_qty",
                    "delivery_docname": "delivery_note",
                    "delivery_childname": "dn_detail",
                },
                "field_no_map": {
                    "full_rate",
                    "full_qty",
                    "series",
                },
                "postprocess": account_details,
            }
        }

        doclist = get_mapped_doc(
            "Sales Invoice",
            source_name,
            fields,
            target_doc,
            set_target_values,
            ignore_permissions=ignore_permissions
        )

        return doclist

    # If company is authorized then only cancel another invoice
    if authority == "Authorized":
        si = get_sales_invoice_entry(self.name)
        si.flags.ignore_permissions = True
        try:
            si.save(ignore_permissions = True)
            self.db_set('ref_invoice', si.name)
            frappe.db.commit()
            si.submit()
            for i in self.items:
                change_delivery_authority(i.delivery_docname)
        except Exception as e:
            frappe.db.rollback()
            frappe.throw(e)
    
    


# Cancel Invoice on Cancel
def cancel_main_sales_invoice(self):
    if self.ref_invoice:
        si = frappe.get_doc("Sales Invoice", {'ref_invoice':self.name})
    else:
        si = None
    
    if si:
        if si.docstatus == 1:
            si.flags.ignore_permissions = True
            try:
                si.cancel()
                for i in self.items:
                    change_delivery_authority(i.delivery_docname)
            except Exception as e:
                frappe.db.rollback()
                frappe.throw(e)
    else:
        for i in self.items:
            change_delivery_authority(i.delivery_docname)

def delete_sales_invoice(self):
    ref_name = self.ref_invoice
    try:
        frappe.db.set_value("Sales Invoice", self.name, 'ref_invoice', '')    
        frappe.db.set_value("Sales Invoice", ref_name, 'ref_invoice', '') 
        frappe.delete_doc("Sales Invoice", ref_name, force = 1, ignore_permissions=True)  
    except Exception as e:
        frappe.db.rollback()
        frappe.throw(e)
    else:
        frappe.db.commit()