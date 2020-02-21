import frappe
from frappe import _
from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

def before_submit(self,method):
    
    WorkOrder.update_planned_qty = update_planned_qty

def before_cancel(self,method):
    WorkOrder.update_planned_qty = update_planned_qty

def update_planned_qty(self):
    if self.production_item and frappe.db.get_value('Item',self.production_item,'is_stock_item'):
        update_bin_qty(self.production_item, self.fg_warehouse, {
            "planned_qty": get_planned_qty(self.production_item, self.fg_warehouse)
        })

        if self.material_request:
            mr_obj = frappe.get_doc("Material Request", self.material_request)
            mr_obj.update_requested_qty([self.material_request_item])
    
@frappe.whitelist()
def make_workorder_finish(work_order_id):
	work_order = frappe.get_doc("Work Order", work_order_id)
	
	wof = frappe.new_doc("Work Order Finish")
	wof.work_order = work_order_id
	wof.company = work_order.company
	wof.item_code = work_order.production_item
	wof.fg_completed_qty = work_order.qty
	wof.target_warehouse = work_order.fg_warehouse
	wof.source_warehouse = work_order.source_warehouse
	wof.from_bom = work_order.bom_no
	
	return wof

@frappe.whitelist()
def update_work_order_status(doc, qty):
	wo = frappe.get_doc("Work Order", doc)

	if wo.status != "In Process":
		wo.db_set("status", "In Process")

	manufacturing_start_qty = flt(qty) + flt(wo.manufacturing_start_qty)

	wo.db_set('manufacturing_start_qty', flt(manufacturing_start_qty))

def override_work_order_functions():
	WorkOrder.update_work_order_qty = update_work_order_qty

def update_work_order_qty(self):
	"""Update **Manufactured Qty** and **Material Transferred for Qty** in Work Order
			based on Stock Entry"""

	allowance_percentage = flt(frappe.db.get_single_value("Manufacturing Settings",
		"overproduction_percentage_for_work_order"))

	purpose = "Manufacture"
	fieldname = "produced_qty"

	qty = flt(frappe.db.sql("""select sum(fg_completed_qty)
		from `tabStock Entry` where work_order=%s and docstatus=1
		and purpose=%s""", (self.name, purpose))[0][0])

	completed_qty = self.qty + (allowance_percentage/100 * self.qty)
	if qty > completed_qty:
		frappe.throw(_("{0} ({1}) cannot be greater than planned quantity ({2}) in Work Order {3}").format(\
			self.meta.get_label(fieldname), qty, completed_qty, self.name), StockOverProductionError)

	self.db_set(fieldname, qty)

	if self.production_plan:
		self.update_production_plan_status()