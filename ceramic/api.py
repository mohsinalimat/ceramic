import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, cstr, getdate
from frappe.model.mapper import get_mapped_doc
import datetime
from frappe.utils import getdate
from erpnext.accounts.utils import get_fiscal_year
from frappe.desk.notifications import get_filters_for
from frappe.utils import get_url_to_form
import json

check_sub_string = lambda string, sub_string: not string.find(sub_string) == -1

def naming_series_name(name, fiscal, company_series=None):
	if company_series:
		name = name.replace('company_series', str(company_series))
	
	name = name.replace('YYYY', str(datetime.date.today().year))
	name = name.replace('YY', str(datetime.date.today().year)[2:])
	name = name.replace('MM', f'{datetime.date.today().month:02d}')
	name = name.replace('DD', f'{datetime.date.today().day:02d}')
	name = name.replace('fiscal', str(fiscal))
	name = name.replace('#', '')
	name = name.replace('.', '')
	
	return name

@frappe.whitelist()
def get_fiscal(date):
	fy = get_fiscal_year(date)[0]
	fiscal = frappe.db.get_value("Fiscal Year", fy, 'fiscal')

	return fiscal if fiscal else fy.split("-")[0][2:] + fy.split("-")[1][2:]

@frappe.whitelist()
def check_counter_series(name, company_series = None, date = None):
	
	if not date:
		date = datetime.date.today()
	
	
	fiscal = get_fiscal(date)
	
	name = naming_series_name(name, fiscal, company_series)
	
	check = frappe.db.get_value('Series', name, 'current', order_by="name")
	
	if check == 0:
		return 1
	elif check == None:
		frappe.db.sql(f"insert into tabSeries (name, current) values ('{name}', 0)")
		return 1
	else:
		return int(frappe.db.get_value('Series', name, 'current', order_by="name")) + 1

@frappe.whitelist()
def before_naming(self, method):
	#if not hasattr(self, 'amended_from'):
	if not self.get('amended_from') and not self.get('name'):
		date = self.get("transaction_date") or self.get("posting_date") or  self.get("manufacturing_date") or getdate()
		fiscal = get_fiscal(date)
		self.fiscal = fiscal
		self.company_series = frappe.db.get_value("Company", self.company, 'company_series')
		if self.get('series_value'):
			if self.series_value > 0:
				name = naming_series_name(self.naming_series, fiscal,self.company_series)
				
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
	frappe.msgprint('call')
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

	# sales team
	if party_type=="Customer":
		out["sales_team"] = [{
			"sales_person": d.sales_person,
			"allocated_percentage": d.allocated_percentage or None,
			'regional_sales_manager': d.regional_sales_manager,
			'sales_manager': d.sales_manager
		} for d in party.get("sales_team")]

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


@frappe.whitelist()
def restrict_access():
	role_permission_list = frappe.get_all("User Permission", filters = {
		"allow": "Authority", "for_value": "Unauthorized"
	}, fields = ['name', 'system_genrated'], ignore_permissions = True)
	for item in role_permission_list:
		if not item['system_genrated']:
			doc = get_mapped_doc("User Permission", item['name'], {
				"User Permission": {
					"doctype": "Backup User Permission",
				}
			}, ignore_permissions = True)

			try:
				doc.save(ignore_permissions = True)
			except:
				pass
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)
	
	user_list = frappe.get_all("User", filters = {'enabled': 1}, fields = ['email', 'username'], ignore_permissions = True)
	for user in user_list:
		if user['username'] != 'administrator' and user['email'] != 'guest@example.com':
			
			if not frappe.db.exists({
				'doctype': 'User Permission',
				'user': user['email'],
				'allow': 'Authority',
				'for_value': 'Authorized'
			}):
				doc = frappe.new_doc("User Permission")

				doc.user = user['email']
				doc.allow = 'Authority'
				doc.for_value = 'Authorized'
				doc.apply_to_all_doctypes = 1
				doc.system_genrated = 1

				try:
					doc.save(ignore_permissions = True)
				except:
					pass
	frappe.db.set_value("Global Defaults", "Global Defaults", "restricted_access", 1)
	frappe.db.commit()
	# frappe.msgprint("Restricted Access")
	return "success"

@frappe.whitelist()
def reverse_restrict_access():
	permission_list = frappe.get_all("Backup User Permission")
	for item in permission_list:
		print(item['name'])
		doc = get_mapped_doc("Backup User Permission", item['name'], {
			"Backup User Permission": {
				"doctype": "User Permission",
			}
		})

		doc.save()
		
		frappe.delete_doc("Backup User Permission", item['name'], ignore_permissions = True)
	
	user_permission_list = frappe.get_all("User Permission", filters = {'system_genrated': 1})

	for item in user_permission_list:
		frappe.delete_doc("User Permission", item['name'], ignore_permissions = True)

	frappe.set_value("Global Defaults", "Global Defaults", "restricted_access", 0)
	frappe.db.commit()

	frappe.msgprint("All Permission Reversed")

@frappe.whitelist()
@frappe.read_only()
def get_open_count(doctype, name, items=[]):
	'''Get open count for given transactions and filters

	:param doctype: Reference DocType
	:param name: Reference Name
	:param transactions: List of transactions (json/dict)
	:param filters: optional filters (json/list)'''

	if frappe.flags.in_migrate or frappe.flags.in_install:
		return {
			"count": []
		}

	frappe.has_permission(doc=frappe.get_doc(doctype, name), throw=True)

	meta = frappe.get_meta(doctype)
	links = meta.get_dashboard_data()

	# compile all items in a list
	if not items:
		for group in links.transactions:
			items.extend(group.get("items"))

	if not isinstance(items, list):
		items = json.loads(items)

	out = []
	for d in items:
		if d in links.get("internal_links", {}):
			# internal link
			continue

		filters = get_filters_for(d)
		fieldname = links.get("non_standard_fieldnames", {}).get(d, links.fieldname)
		data = {"name": d}
		if filters:
			# get the fieldname for the current document
			# we only need open documents related to the current document
			filters[fieldname] = name
			total = len(frappe.get_list(d, fields="name",
				filters=filters, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
			data["open_count"] = total

		total = len(frappe.get_list(d, fields="name",
			filters={fieldname: name}, limit=100, distinct=True, ignore_ifnull=True, user = frappe.session.user))
		data["count"] = total
		out.append(data)

	out = {
		"count": out,
	}

	module = frappe.get_meta_module(doctype)
	if hasattr(module, "get_timeline_data"):
		out["timeline_data"] = module.get_timeline_data(doctype, name)

	return out

def item_patch():
	data = frappe.db.sql("SELECT * FROM `tabItem` WHERE is_tile = 1 and tile_quality = 'Premium' AND is_item_series = 0", as_dict = 1)
	tile_categries = ['Premium', 'Golden', 'Economy', 'Classic']

	for item in data:
		if not frappe.db.exists("Tile Item Creation Tool", item.item_name.replace("-Premium", '')):
			tile_item = frappe.new_doc("Tile Item Creation Tool")
			tile_item.item_name = item.item_name.replace("-Premium", '')
		else:
			tile_item = frappe.get_doc("Tile Item Creation Tool", item.item_name.replace("-Premium", ''))
			if tile_item.docstatus == 1:
				continue
		tile_item.item_series = item.item_series
		tile_item.item_group = item.item_group
		tile_item.item_design = item.item_design
		
		tile_item.tile_quality = []
		tile_item.default_production_price = 0

		tile_item.image = item.image
		tile_item.cover_image = item.cover_image

		for j in tile_categries:
			item_name = item.item_name.replace('Premium', j)
			item_doc = frappe.get_doc('Item', {'item_name': item_name})
			item_doc.db_set("item_creation_tool", tile_item.item_name)

			tile_item.append('tile_quality', {
				'tile_quality': j,
				'item_code': item_doc.item_code,
				'production_price': 0
			})


			tile_item.item_defaults = []
			for k in item_doc.item_defaults:
				tile_item.append('item_defaults', {
					'company': k.company,
					'default_warehouse': k.default_warehouse,
				})
			
			if item_doc.show_in_website:
				tile_item.show_in_website = 1
				tile_item.weightage = item_doc.weightage
				tile_item.slideshow = item.slideshow
				tile_item.website_warehouse = item.website_warehouse
				tile_item.website_image = item.website_image
		lst = []
		
		for k in tile_item.tile_quality:
			if k.tile_quality:
				lst.append(k)

		tile_item.tile_quality = []
		tile_item.tile_quality = lst
			
		tile_item.save()
		
		frappe.db.commit()
		
		print(tile_item.item_name)

def tile_item_creation_update():
	data = frappe.get_all("Tile Item Creation Tool")

	for item in data:
		doc = frappe.get_doc("Tile Item Creation Tool", item.name)

		doc.item_defaults = []

		doc.append('item_defaults', {
			'company': 'Millennium Vitrified Tiles Pvt. Ltd. Testing',
			'default_warehouse': 'Stores - MVTT'
		})

		for tile in doc.tile_quality:
			item_price = frappe.get_doc("Item Price", {'item_code': tile.item_code})
			
			tile.production_price = item_price.price_list_rate
			doc.default_production_price = item_price.price_list_rate

		doc.save()
		frappe.db.commit()
		print(doc.name)

@frappe.whitelist()
def create_pick_list(source_name, target_doc=None):
	frappe.throw("Testing")


@frappe.whitelist()	
def sales_order_query(doctype, txt, searchfield, start, page_len, filters):
	conditions = []

	so_searchfield = frappe.get_meta("Sales Order").get_search_fields()
	so_searchfields = " or ".join(["so.`" + field + "` like %(txt)s" for field in so_searchfield])

	soi_searchfield = frappe.get_meta("Sales Order Item").get_search_fields()
	soi_searchfield += ["item_code"]
	soi_searchfields = " or ".join(["soi.`" + field + "` like %(txt)s" for field in soi_searchfield])

	searchfield = so_searchfields + " or " + soi_searchfields

	where_condition = ''
	if filters.get("item_code"):
		where_condition += " and soi.item_code = '{}'".format(filters.get("item_code"))
	
	if filters.get("customer"):
		where_condition += " and so.customer = '{}'".format(filters.get("customer"))

	return frappe.db.sql("""select so.name, so.status, so.transaction_date, so.customer, soi.item_code
			from `tabSales Order` so
		RIGHT JOIN `tabSales Order Item` soi ON (so.name = soi.parent)
		where so.docstatus = 1
			and so.status != "Closed" {where_condition}
			and ({searchfield})
			and so.company = '{company}'
		order by
			if(locate(%(_txt)s, so.name), locate(%(_txt)s, so.name), 99999)
		limit %(start)s, %(page_len)s """.format(searchfield=searchfield, where_condition = where_condition, company = filters.get("company")), {
			'txt': '%%%s%%' % txt,
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'item_code': filters.get('item_code'),
			'customer': filters.get('customer')
		})

from erpnext.accounts.doctype.gl_entry.gl_entry import update_against_account
def invoice_date_patch():
	# for doc in frappe.get_all("Sales Invoice", {'authority': 'Authorized', 'docstatus': 1}, ['name','posting_date', 'due_date', 'customer', 'si_ref']):
	# 	doc2 = frappe.get_doc("Sales Invoice", doc.si_ref)
		
	# 	doc2.posting_date = doc.posting_date
	# 	doc2.due_date = doc.due_date
	# 	doc2.save()

	# 	print(doc2.customer)
	
	for doc in frappe.get_all("Sales Invoice", ['name', 'posting_date', 'customer']):
		frappe.db.sql("""update `tabGL Entry` set posting_date=%s
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			(doc.posting_date, doc.name))

		print(doc.posting_date)

	frappe.db.commit()

@frappe.whitelist()
def get_lot_wise_data(item_code, company, from_date, to_date):
	float_precision = 2
	from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
	to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
	def get_conditions(item_code, company, from_date, to_date):
		conditions = ""
		conditions += f" and posting_date <= '{to_date}'"
		conditions += f" and company = '{company}'"
		conditions += f" and item_code = '{item_code}'"

		return conditions

	def get_stock_ledger_entries(item_code, company, from_date, to_date):
		conditions = get_conditions(item_code, company, from_date, to_date)
		return frappe.db.sql(f"""
			select item_code, batch_no, warehouse, posting_date, sum(actual_qty) as actual_qty
			from `tabStock Ledger Entry`
			where docstatus < 2 and ifnull(batch_no, '') != '' {conditions}
			group by voucher_no, batch_no, item_code, warehouse
			order by item_code, warehouse""", as_dict=1)
		

	def get_item_warehouse_batch_map(item_code, company, from_date, to_date):
		sle = get_stock_ledger_entries(item_code, company, from_date, to_date)
		iwb_map = {}

		for d in sle:
			iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {})\
				.setdefault(d.batch_no, frappe._dict({
					"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0
				}))
			qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
			if d.posting_date < from_date:
				qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
					+ flt(d.actual_qty, float_precision)
			elif d.posting_date >= from_date and d.posting_date <= to_date:
				if flt(d.actual_qty) > 0:
					qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
				else:
					qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
						+ abs(flt(d.actual_qty, float_precision))

			qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
		return iwb_map

	iwb_map =  get_item_warehouse_batch_map(item_code, company, from_date, to_date)
	data = []
	conditions = get_conditions(item_code, company, from_date, to_date)
	for item in sorted(iwb_map):
		if item_code == item:
			for wh in sorted(iwb_map[item]):
				for batch in sorted(iwb_map[item][wh]):
					qty_dict = iwb_map[item][wh][batch]
					picked_qty = frappe.db.sql(f"""
					SELECT sum(pli.qty - pli.delivered_qty) FROM `tabPick List Item` as pli JOIN `tabPick List` as pl on pli.parent = pl.name 
					WHERE pli.item_code = '{item}' AND pli.warehouse='{wh}' AND pli.batch_no='{batch}' and pl.docstatus = 1 {conditions}
					""")[0][0] or 0.0
					lot_no = frappe.db.get_value("Batch", batch, 'lot_no')
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						data.append({
							'item_code': item,
							'item_name': frappe.db.get_value("Item", item, 'item_name'),
							'lot_no': lot_no,
							'bal_qty': flt(qty_dict.bal_qty, float_precision),
							'picked_qty': picked_qty,
							'remaining_qty': flt(qty_dict.bal_qty, float_precision) - picked_qty,
							'opening_qty': flt(qty_dict.opening_qty, float_precision),
							'in_qty': flt(qty_dict.in_qty, float_precision),
							'out_qty': flt(qty_dict.out_qty, float_precision), 
							'warehouse': wh,
						})
	return data

@frappe.whitelist()
def get_picked_item(item_code, batch_no, company, from_date, to_date, bal_qty, total_picked_qty, total_remaining_qty, lot_no):
	float_precision = 2
	from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
	to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()

	picked_item = frappe.db.sql(f"""
		SELECT 
			pli.date, pli.sales_order, pli.sales_order_item,
			pl.name as pick_list, pli.name as pick_list_item, pli.item_code,
			pli.item_name, (pli.qty - pli.delivered_qty - pli.wastage_qty) as picked_qty,
			pli.delivered_qty, (pli.qty - (pli.wastage_qty + pli.delivered_qty)) as remaining_qty,
			so.title as customer, so.order_rank
		FROM 
			`tabPick List Item` as pli JOIN `tabPick List` as pl on pli.parent = pl.name
			JOIN `tabSales Order` as so on pli.sales_order = so.name
		WHERE
			pl.docstatus = 1 AND pli.item_code = '{item_code}' AND 
			pli.batch_no = '{batch_no}' AND pl.company = '{company}' 
			AND pl.posting_date <= '{to_date}'
		HAVING
			remaining_qty > 0
		ORDER BY
			so.order_rank
	""", as_dict = 1)
	
	for item in picked_item:
		url = get_url_to_form("Sales Order", item.sales_order)
		sales_order_link = "<a href='{url}'>{name}</a>".format(url=url, name=item.sales_order)
		pickurl = get_url_to_form("Pick List", item.pick_list)
		pick_list_link = "<a href='{pickurl}'>{name}</a>".format(pickurl=pickurl, name=item.pick_list)		
		item.sales_order_link = sales_order_link
		item.pick_list_link = pick_list_link
		item.bal_qty = bal_qty
		item.total_picked_qty = total_picked_qty
		item.total_remaining_qty = total_remaining_qty
		item.lot_no = lot_no
	
	if not picked_item:
		picked_item = [{
			'bal_qty': bal_qty,
			'total_picked_qty': total_picked_qty,
			'total_remaining_qty': total_remaining_qty,
			'lot_no': lot_no,
			'item_name': frappe.db.get_value("Item", item_code, 'item_name')
		}]
	
	
	return picked_item

def naming_series_validate(self, method):
	if self.get('company_series'):
		if not frappe.db.exists("Company", {'name': self.company, 'company_series': self.company_series}):
			frappe.throw("You can not change company")

def pi_patch():
	pi_list = frappe.db.sql("select name from `tabPurchase Invoice` WHERE authority = 'Unauthorized'")

	for pi in pi_list:
		pi_doc = frappe.get_doc("Purchase Invoice", pi[0])
		pi_doc.discounted_total = sum(x.discounted_amount for x in pi_doc.items)
		pi_doc.discounted_net_total = sum(x.discounted_net_amount for x in pi_doc.items)
		testing_only_tax = 0
		
		for tax in pi_doc.taxes:
			if tax.testing_only:
				testing_only_tax += tax.tax_amount
		
		pi_doc.discounted_grand_total = pi_doc.discounted_net_total + pi_doc.total_taxes_and_charges - testing_only_tax
		if pi_doc.rounded_total:
			pi_doc.discounted_rounded_total = round(pi_doc.discounted_grand_total)
		pi_doc.real_difference_amount = (pi_doc.rounded_total or pi_doc.grand_total) - (pi_doc.discounted_rounded_total or pi_doc.discounted_grand_total)
		pi_doc.pay_amount_left = pi_doc.real_difference_amount
		pi_doc.flags.ignore_validate_update_after_submit = True
		pi_doc.save()
	
	frappe.db.commit()

def pi_patch():
	pi_list = frappe.db.sql("Select name from `tabPurchase Invoice` WHERE pi_ref is null and authority = 'Unauthorized'")

	for pi in pi_list:
		pi_doc = frappe.get_doc("Purchase Invoice", pi[0])

		for item in pi_doc.items:
			item.discounted_rate = item.real_qty = item.discounted_amount = item.discounted_net_amount = 0
		
		pi_doc.pay_amount_left  = pi_doc.real_difference_amount = pi_doc.rounded_total or pi_doc.grand_total
		pi_doc.discounted_grand_total = pi_doc.discounted_rounded_total = 0

		pi_doc.flags.ignore_validate_update_after_submit = True

		pi_doc.save()
	
	frappe.db.commit()

from frappe.utils import flt
def po_ref_match_patch():
	pi_list = frappe.get_list("Purchase Invoice", {"authority": "Authorized"})
	po = []

	for pi in pi_list:
		pi_authorized_doc = frappe.get_doc("Purchase Invoice", pi['name'])
		pi_unauthorized_doc = frappe.get_doc("Purchase Invoice", pi_authorized_doc.pi_ref)

		for item in pi_authorized_doc.items:
			item.po_docname = frappe.db.get_value("Purchase Receipt Item", item.purchase_receipt_childname, 'purchase_order')
			item.po_childname = frappe.db.get_value("Purchase Receipt Item", item.purchase_receipt_childname, 'purchase_order_item')
			print(item.po_docname)
			print(item.po_childname)
		
		for item in pi_unauthorized_doc.items:
			item.purchase_order = frappe.db.get_value("Purchase Receipt Item", item.pr_detail, 'purchase_order')
			item.po_detail = frappe.db.get_value("Purchase Receipt Item", item.pr_detail, 'purchase_order_item')
			billed_amt, parent = frappe.db.get_value("Purchase Order Item", item.po_detail, ['billed_amt', 'parent'])
			frappe.db.set_value("Purchase Order Item", item.po_detail,'billed_amt', (flt(billed_amt) + flt(item.amount)))
	
		pi_authorized_doc.flags.ignore_validate_update_after_submit = True
		pi_unauthorized_doc.flags.ignore_validate_update_after_submit = True
		pi_authorized_doc.save()
		pi_unauthorized_doc.save()

		for item in set(po):
			po_doc = frappe.get_doc("Purchase Order", item)

			amt = 0
			for row in po_doc.items:
				row += row.billed_amt
			
			per_billed = (amt / total) * 100
			p
			po_doc.db_set('per_billed', per_billed)
			
			if per_billed >= '100':
				po_doc.db_set('status', 'completed')
		
	
	frappe.db.commit()

from erpnext.stock.doctype.purchase_receipt.purchase_receipt import update_billed_amount_based_on_po

def update_billing_status_in_pr(self, update_modified=True):
	updated_pr = []
	for d in self.get("items"):
		if d.po_detail:
			updated_pr += update_billed_amount_based_on_po(d.po_detail, update_modified)

	for pr in set(updated_pr):
		frappe.get_doc("Purchase Receipt", pr).update_billing_percentage(update_modified=update_modified)

def update_po():
	for item in frappe.get_all("Purchase Order"):
		po_doc = frappe.get_doc("Purchase Order", item.name)

		amt = 0
		for row in po_doc.items:
			amt += flt(row.billed_amt)
		per_billed = flt((amt / po_doc.total) * 100)
		
		po_doc.db_set('per_billed', per_billed)
		
		if per_billed >= 100:
			po_doc.db_set('status', 'Completed')
	
	frappe.db.commit()

@frappe.whitelist()
def test():
    return "hello"

# console patches
from ceramic.ceramic.doc_events.sales_order import update_sales_order_total_values
def update_so_wastage_qty():
	sales_order_item_list = frappe.get_list("Sales Order Item", {'docstatus': 1})

	for i in sales_order_item_list:
		doc = frappe.get_doc("Sales Order Item", i.name)

		wastage_qty, picked_qty = frappe.db.get_value("Pick List Item", {'docstatus': 1, 'sales_order_item': i.name}, ['sum(wastage_qty)', 'sum(qty)'])

		if wastage_qty or picked_qty:
			print(doc.parent)
			if wastage_qty != doc.wastage_qty:
				doc.db_set('wastage_qty', wastage_qty or 0.0, update_modified = False)
			if picked_qty != doc.picked_qty:
				doc.db_set('picked_qty', picked_qty or 0.0, update_modified = False)
	
	frappe.db.commit()

def sales_order_item_patch():
	data = frappe.get_list("Sales Order Item", ['name', 'sales_order_item'])

	for item in data:
		if not frappe.db.exists("Sales Order Item", item.sales_order_item):
			print(item.name)
			# pl = frappe.get_doc("Pick List Item", item.name)

			# if pl.docstatus == 1:
			# 	pl.cancel()
			# pl.delete()

# update `tabPick List Item` qty = delivered_qty + wastage_qty  WHERE qty < delivered_qty + wastage_qty
from ceramic.ceramic.report.accounts_receivable_ceramic.accounts_receivable_ceramic import ReceivablePayableReport
import json
@frappe.whitelist()
def get_payment_remark_details(filters):
	filters = json.loads(filters)
	args = {
		"party_type": "Customer",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	data = ReceivablePayableReport(filters).run(args)[1]
	new_data = {}

	for x in data:
		company = x.company

		if frappe.db.get_value("Company", x.company, 'authority') == "Unauthorized":
			company = frappe.db.get_value("Company", x.company, 'alternate_company')

		if not new_data.get(company):
			new_data[company] = []
		
		new_data[company].append(x)
	
	table = ""

	for key, value in new_data.items():
		if value:
			table += f"<h2>{key}</h2>"
			table += """<table class="table table-bordered" style="margin: 0; font-size:80%;">
			<thead>
				<tr>
					<th>Voucher No</th>
					<th>Posting Date</th>
					<th>Total Outstanding</th>
					<th>Bank Outstanding</th>
					<th>Cash Outstanding</th>
				<tr>
			</thead>
			<tbody>"""

			total_outstanding = 0
			total_bank_outstanding = 0
			total_cash_outstanding = 0

			for x in value:
				total_outstanding += x.outstanding
				total_bank_outstanding += x.bank_outstanding
				total_cash_outstanding += x.cash_outstanding
				table += f"""
					<tr>
						<td>{x.voucher_no}</td>
						<td>{x.posting_date}</td>
						<td>{x.outstanding}</td>
						<td>{x.bank_outstanding}</td>
						<td>{x.cash_outstanding}</td>
					</tr>
				"""
			
			table += f"""
				<tr>
					<td>Total</td>
					<td></td>
					<td>{total_outstanding}</td>
					<td>{total_bank_outstanding}</td>
					<td>{total_cash_outstanding}</td>
				</tr>
			"""
			
			table += """
			</tbody>
			</table>
			"""
	
	return table

	
	# table +=
	# 			{% for (let row of data ) { %}
	# 				<tr class="{{ __(row['pick_list_item']) }}">
	# 					<td>{{ __(row['customer']) }}</td>
	# 					<td>{{ __(row['order_rank']) }}</td>
	# 					<td>{{ __(row['sales_order_link']) }}</td>
	# 					<td>{{ __(row['date']) }}</td>
	# 					<td>{{ __(row['pick_list_link']) }}</td>
	# 					<td>{{ __(row['picked_qty']) }}</td>
	# 					<td><input type="float" style="width:50px" id="{{ row['pick_list_item'] }}"></input></td>
	# 					<td><button style="margin-left:5px;border:none;color: #fff; background-color: red; padding: 3px 5px;border-radius: 5px;" type="button" sales-order="{{ __(row['sales_order']) }}" sales-order-item="{{ __(row['sales_order_item']) }}" pick-list="{{ __(row['pick_list']) }}" pick-list-item="{{ __(row['pick_list_item']) }}" onClick=remove_picked_item_lot_wise(this.getAttribute("sales-order"),this.getAttribute("sales-order-item"),this.getAttribute("pick-list"),this.getAttribute("pick-list-item"),document.getElementById("{{ row['pick_list_item'] }}").value)>Unpick</button></td>
	# 				</tr>
	# 			{% } %}
	