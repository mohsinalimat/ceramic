import frappe
from frappe import _

@frappe.whitelist()
def validate_item_authority(self,method):
    throw_validation,ignore_flag_for_dn = False,False
    for row in self.items:
        if row.item_code:
            if frappe.db.get_value("Item",row.item_code,'is_stock_item'):
                if frappe.db.get_value("Item", row.item_code, 'authority') != self.authority and not self.get('ignore_item_validate'):
                    if self.doctype == 'Delivery Note' and row.against_sales_order and row.so_detail:
                        if row.item_code != frappe.db.get_value("Sales Order Item",row.so_detail,"item_code"):
                            throw_validation = True
                        else:
                            ignore_flag_for_dn = True
                    else:
                        throw_validation = True

            if throw_validation:
                frappe.throw(_("Row:{0} Not allowed to create {1} for {2} in {3}, please ensure item/item_series has been selected correctly.".format(row.idx,self.doctype,row.item_code,self.company)))
    
    if ignore_flag_for_dn:
        self.ignore_batch_validate = True