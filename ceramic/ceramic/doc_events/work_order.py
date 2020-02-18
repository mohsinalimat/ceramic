import frappe
from frappe import _

def before_submit(self,method):
    from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
    WorkOrder.update_planned_qty = update_planned_qty

def before_cancel(self,method):
    from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
    WorkOrder.update_planned_qty = update_planned_qty

def update_planned_qty(self):
    if self.production_item and frappe.db.get_value('Item',self.production_item,'is_stock_item'):
        update_bin_qty(self.production_item, self.fg_warehouse, {
            "planned_qty": get_planned_qty(self.production_item, self.fg_warehouse)
        })

        if self.material_request:
            mr_obj = frappe.get_doc("Material Request", self.material_request)
            mr_obj.update_requested_qty([self.material_request_item])