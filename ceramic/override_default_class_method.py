import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, format_time, floor
from erpnext.stock.stock_ledger import get_previous_sle, NegativeStockError
from erpnext.stock.doctype.pick_list.pick_list import get_available_item_locations_for_batched_item
from frappe.model.naming import parse_naming_series
from frappe.permissions import get_doctypes_with_read

def create_payment_entry(self, pe):
	payment = frappe.new_doc("Payment Entry")
	payment.posting_date = pe.transaction_date
	payment.payment_type = "Receive" if pe.party_type == "Customer" else "Pay"
	payment.primary_customer = pe.primary_customer
	payment.company = self.company
	payment.mode_of_payment = "Wire Transfer"
	payment.party_type = pe.party_type
	payment.party = pe.party
	payment.paid_to = self.bank_account if pe.party_type == "Customer" else self.payable_account
	payment.paid_from = self.receivable_account if pe.party_type == "Customer" else self.bank_account
	payment.paid_amount = payment.received_amount = abs(pe.amount)
	payment.reference_no = pe.description
	payment.reference_date = pe.transaction_date
	payment.save()
	for inv_entry in self.payment_invoice_items:
		if (pe.description != inv_entry.payment_description or pe.transaction_date != inv_entry.transaction_date): continue
		if (pe.party != inv_entry.party): continue
		reference = payment.append("references", {})
		reference.reference_doctype = inv_entry.invoice_type
		reference.reference_name = inv_entry.invoice
		reference.allocated_amount = inv_entry.allocated_amount
		print ("Adding invoice {0} {1}".format(reference.reference_name, reference.allocated_amount))
	payment.setup_party_account_field()
	payment.set_missing_values()
	#payment.set_exchange_rate()
	#payment.set_amounts()
	#print("Created payment entry {0}".format(payment.as_dict()))
	payment.save()
	return payment

def raise_exceptions(self):
	deficiency = min(e["diff"] for e in self.exceptions)

	if ((self.exceptions[0]["voucher_type"], self.exceptions[0]["voucher_no"]) in
		frappe.local.flags.currently_saving):

		msg = _("{0} units of {1} needed in {2} to complete this transaction.").format(
			abs(deficiency), frappe.get_desk_link('Item', self.item_code),
			frappe.get_desk_link('Warehouse', self.warehouse))
	else:
		msg = _("{0} units of {1} needed in {2} on {3} {4} for {5} to complete this transaction.").format(
			abs(deficiency), frappe.get_desk_link('Item', self.item_code),
			frappe.get_desk_link('Warehouse', self.warehouse),
			self.exceptions[0]["posting_date"], self.exceptions[0]["posting_time"],
			frappe.get_desk_link(self.exceptions[0]["voucher_type"], self.exceptions[0]["voucher_no"]))

	allow_negative_stock = frappe.db.get_value("Company", self.company, "allow_negative_stock")
	
	if not allow_negative_stock:
		if self.verbose:
			frappe.throw(msg, NegativeStockError, title='Insufficent Stock')
		else:
			raise NegativeStockError(msg)

def set_actual_qty(self):
	allow_negative_stock = cint(frappe.db.get_value("Stock Settings", None, "allow_negative_stock")) or cint(frappe.db.get_value("Company", self.company, "allow_negative_stock"))

	for d in self.get('items'):
		previous_sle = get_previous_sle({
			"item_code": d.item_code,
			"warehouse": d.s_warehouse or d.t_warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time
		})

		# get actual stock at source warehouse
		d.actual_qty = previous_sle.get("qty_after_transaction") or 0

		# validate qty during submit
		if d.docstatus==1 and d.s_warehouse and not allow_negative_stock and flt(d.actual_qty, d.precision("actual_qty")) < flt(d.transfer_qty, d.precision("actual_qty")):
			frappe.throw(_("Row {0}: Quantity not available for {4} in warehouse {1} at posting time of the entry ({2} {3})").format(d.idx,
				frappe.bold(d.s_warehouse), formatdate(self.posting_date),
				format_time(self.posting_time), frappe.bold(d.item_code))
				+ '<br><br>' + _("Available quantity is {0}, you need {1}").format(frappe.bold(d.actual_qty),
					frappe.bold(d.transfer_qty)),
				NegativeStockError, title=_('Insufficient Stock'))

def get_available_item_locations(item_code, from_warehouses, required_qty):
	locations = []
	if frappe.get_cached_value('Item', item_code, 'has_serial_no'):
		locations = get_available_item_locations_for_serialized_item(item_code, from_warehouses, required_qty)
	elif frappe.get_cached_value('Item', item_code, 'has_batch_no'):
		locations = get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty)
	else:
		locations = get_available_item_locations_for_other_item(item_code, from_warehouses, required_qty)

	total_qty_available = sum(location.get('qty') for location in locations)

	remaining_qty = required_qty - total_qty_available

	if remaining_qty > 0:
		frappe.msgprint(_('{0} units of {1} is not available.')
			.format(remaining_qty, frappe.get_desk_link('Item', item_code)))

	return locations

def get_items_with_location_and_quantity(item_doc, item_location_map):
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []

	remaining_stock_qty = item_doc.stock_qty
	while remaining_stock_qty > 0 and available_locations:
		item_location = available_locations.pop(0)
		item_location = frappe._dict(item_location)

		stock_qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		qty = stock_qty / (item_doc.conversion_factor or 1)

		uom_must_be_whole_number = frappe.db.get_value('UOM', item_doc.uom, 'must_be_whole_number')
		if uom_must_be_whole_number:
			qty = floor(qty)
			stock_qty = qty * item_doc.conversion_factor
			if not stock_qty: break

		serial_nos = None
		if item_location.serial_no:
			serial_nos = '\n'.join(item_location.serial_no[0: cint(stock_qty)])

		locations.append(frappe._dict({
			'qty': qty,
			'stock_qty': stock_qty,
			'warehouse': item_location.warehouse,
			'serial_no': serial_nos,
			'batch_no': item_location.batch_no
		}))

		remaining_stock_qty -= stock_qty

		qty_diff = item_location.qty - stock_qty
		# if extra quantity is available push current warehouse to available locations
		if qty_diff > 0:
			item_location.qty = qty_diff
			if item_location.serial_no:
				# set remaining serial numbers
				item_location.serial_no = item_location.serial_no[-qty_diff:]
			available_locations = [item_location] + available_locations

	# update available locations for the item
	item_location_map[item_doc.item_code] = available_locations
	return locations

def set_item_locations(self):
	items = self.aggregate_item_qty()
	self.item_location_map = frappe._dict()

	from_warehouses = None
	if self.parent_warehouse:
		from_warehouses = frappe.db.get_descendants('Warehouse', self.parent_warehouse)

	# reset
	self.delete_key('locations')
	for item_doc in items:
		item_code = item_doc.item_code

		self.item_location_map.setdefault(item_code,
			get_available_item_locations(item_code, from_warehouses, self.item_count_map.get(item_code)))

		locations = get_items_with_location_and_quantity(item_doc, self.item_location_map)

		item_doc.idx = None
		item_doc.name = None

		for row in locations:
			row.update({
				'picked_qty': row.stock_qty
			})

			location = item_doc.as_dict()
			location.update(row)
			self.append('locations', location)

def set_item_locations(self):
	pass

def get_current_tax_amount(self, item, tax, item_tax_map):
		tax_rate = self._get_tax_rate(tax, item_tax_map)
		current_tax_amount = 0.0

		if tax.charge_type == "Actual":
			# distribute the tax amount proportionally to each item row
			actual = flt(tax.tax_amount, tax.precision("tax_amount"))
			current_tax_amount = item.net_amount*actual / self.doc.net_total if self.doc.net_total else 0.0

		elif tax.charge_type == "On Net Total":
			if self.doc.authority == "Unauthorized":
				current_tax_amount = (tax_rate / 100.0) * item.discounted_net_amount
			else:
				current_tax_amount = (tax_rate / 100.0) * item.net_amount
		elif tax.charge_type == "On Previous Row Amount":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].tax_amount_for_current_item
		elif tax.charge_type == "On Previous Row Total":
			current_tax_amount = (tax_rate / 100.0) * \
				self.doc.get("taxes")[cint(tax.row_id) - 1].grand_total_for_current_item
		elif tax.charge_type == "On Item Quantity":
			current_tax_amount = tax_rate * item.stock_qty

		self.set_item_wise_tax(item, tax, tax_rate, current_tax_amount)

		return current_tax_amount

def determine_exclusive_rate(self):
	if not any((cint(tax.included_in_print_rate) for tax in self.doc.get("taxes"))):
		return

	for item in self.doc.get("items"):
		item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
		cumulated_tax_fraction = 0
		for i, tax in enumerate(self.doc.get("taxes")):
			tax.tax_fraction_for_current_item = self.get_current_tax_fraction(tax, item_tax_map)

			if i==0:
				tax.grand_total_fraction_for_current_item = 1 + tax.tax_fraction_for_current_item
			else:
				tax.grand_total_fraction_for_current_item = \
					self.doc.get("taxes")[i-1].grand_total_fraction_for_current_item \
					+ tax.tax_fraction_for_current_item

			cumulated_tax_fraction += tax.tax_fraction_for_current_item
		if cumulated_tax_fraction and not self.discount_amount_applied and item.qty:
			# Finbyz Changes for Tax Calculation on Real Rate
			if self.doc.authority == "Unauthorized":
				# item.discounted_amount = item.discounted_rate * item.real_qty
				amount_diff = item.amount - item.discounted_amount
				if tax.tax_exclusive == 1:
					item.discounted_net_amount = flt(item.amount - amount_diff)
					item.net_amount = item.amount - ((flt(item.amount - amount_diff)) * cumulated_tax_fraction)
				else:
					item.discounted_net_amount = flt((item.amount - amount_diff) / (1 + cumulated_tax_fraction))
					item.net_amount = item.amount - (item.discounted_amount - item.discounted_net_amount)
				
				try:
					item.discounted_net_rate = flt(item.discounted_net_amount / item.real_qty)
				except:
					item.discounted_net_rate = 0
								
				
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
			# Finbyz Changes end here.
			else:
				item.net_amount = flt(item.amount / (1 + cumulated_tax_fraction))
				item.net_rate = flt(item.net_amount / item.qty, item.precision("net_rate"))
			item.discount_percentage = flt(item.discount_percentage,
				item.precision("discount_percentage"))

			self._set_in_company_currency(item, ["net_rate", "net_amount"])

def calculate_taxes(self):
	self.doc.rounding_adjustment = 0
	# maintain actual tax rate based on idx
	actual_tax_dict = dict([[tax.idx, flt(tax.tax_amount, tax.precision("tax_amount"))]
		for tax in self.doc.get("taxes") if tax.charge_type == "Actual"])

	for n, item in enumerate(self.doc.get("items")):
		item_tax_map = self._load_item_tax_rate(item.item_tax_rate)
		for i, tax in enumerate(self.doc.get("taxes")):
			# tax_amount represents the amount of tax for the current step
			current_tax_amount = self.get_current_tax_amount(item, tax, item_tax_map)

			# Adjust divisional loss to the last item
			if tax.charge_type == "Actual":
				actual_tax_dict[tax.idx] -= current_tax_amount
				if n == len(self.doc.get("items")) - 1:
					current_tax_amount += actual_tax_dict[tax.idx]

			# accumulate tax amount into tax.tax_amount
			if tax.charge_type != "Actual" and \
				not (self.discount_amount_applied and self.doc.apply_discount_on=="Grand Total"):
					tax.tax_amount += current_tax_amount

			# store tax_amount for current item as it will be used for
			# charge type = 'On Previous Row Amount'
			tax.tax_amount_for_current_item = current_tax_amount

			# set tax after discount
			tax.tax_amount_after_discount_amount += current_tax_amount

			current_tax_amount = self.get_tax_amount_if_for_valuation_or_deduction(current_tax_amount, tax)

			# note: grand_total_for_current_item contains the contribution of
			# item's amount, previously applied tax and the current tax on that item
			if i==0:
				# Finbyz Changes Start
				if self.doc.authority == "Unauthorized":
					tax.grand_total_for_current_item = flt(item.discounted_net_amount + current_tax_amount)
				# Finbuz Changes End
				else:
					tax.grand_total_for_current_item = flt(item.net_amount + current_tax_amount)
			else:
				tax.grand_total_for_current_item = \
					flt(self.doc.get("taxes")[i-1].grand_total_for_current_item + current_tax_amount)

			# set precision in the last item iteration
			if n == len(self.doc.get("items")) - 1:
				self.round_off_totals(tax)
				self.set_cumulative_total(i, tax)

				self._set_in_company_currency(tax,
					["total", "tax_amount", "tax_amount_after_discount_amount"])

				# adjust Discount Amount loss in last tax iteration
				if i == (len(self.doc.get("taxes")) - 1) and self.discount_amount_applied \
					and self.doc.discount_amount and self.doc.apply_discount_on == "Grand Total":
						self.doc.rounding_adjustment = flt(self.doc.grand_total
							- flt(self.doc.discount_amount) - tax.total,
							self.doc.precision("rounding_adjustment"))

def get_transactions(self, arg=None):
	doctypes = list(set(frappe.db.sql_list("""select parent
			from `tabDocField` df where fieldname='naming_series'""")
		+ frappe.db.sql_list("""select dt from `tabCustom Field`
			where fieldname='naming_series'""")))

	doctypes = list(set(get_doctypes_with_read()).intersection(set(doctypes)))
	prefixes = ""
	for d in doctypes:
		options = ""
		try:
			options = self.get_options(d)
		except frappe.DoesNotExistError:
			frappe.msgprint(_('Unable to find DocType {0}').format(d))
			#frappe.pass_does_not_exist_error()
			continue
			
		#finbyz
		if options:
			options = get_naming_series_options(d)
			prefixes = prefixes + "\n" + options
	prefixes.replace("\n\n", "\n")
	prefixes = sorted(list(set(prefixes.split("\n"))))

	custom_prefixes = frappe.get_all('DocType', fields=["autoname"],
		filters={"name": ('not in', doctypes), "autoname":('like', '%.#%'), 'module': ('not in', ['Core'])})
	if custom_prefixes:
		prefixes = prefixes + [d.autoname.rsplit('.', 1)[0] for d in custom_prefixes]

	prefixes = "\n".join(sorted(prefixes))

	return {
		"transactions": "\n".join([''] + sorted(doctypes)),
		"prefixes": prefixes
	}

#finbyz
def get_naming_series_options(doctype):
	meta = frappe.get_meta(doctype)
	options = meta.get_field("naming_series").options.split("\n")	
	options_list = []

	fields = [d.fieldname for d in meta.fields]
	# frappe.msgprint(str(len(options)))

	for option in options:
		parts = option.split('.')

		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		naming_str = parse_naming_series(parts)
		series = {}
		dynamic_field = {}
		field_list = []
		
		for part in parts:
			if part in fields:
				field_list.append(part)
				dynamic_field[part] = (frappe.db.sql_list("select distinct {field} from `tab{doctype}` where {field} is not NULL".format(field=part, doctype=doctype)))
	
		import itertools
		if dynamic_field.items():
			pair = [(k, v) for k, v in dynamic_field.items()]
			key = [item[0] for item in pair]
			value = [item[1] for item in pair]

			combination = list(itertools.product(*value))
			for item in combination:
				name = naming_str
				for k, v in zip(key, item):
					name = name.replace(k, v)

				options_list.append(name)
		
	return "\n".join(options_list)

#check for item quantity available in stock
def actual_amt_check(self):
	if self.batch_no and not self.get("allow_negative_stock"):
		batch_bal_after_transaction = flt(frappe.db.sql("""select sum(actual_qty)
			from `tabStock Ledger Entry`
			where warehouse=%s and item_code=%s and batch_no=%s""",
			(self.warehouse, self.item_code, self.batch_no))[0][0])

		if batch_bal_after_transaction < 0:
			frappe.throw(_("Stock balance in Batch {0} will become negative {1} for Item {2} at Warehouse {3}")
				.format(self.batch_no, batch_bal_after_transaction, self.item_code, self.warehouse))

		batch_bal_after_transaction_without_warehouse = flt(frappe.db.sql("""select sum(actual_qty)
			from `tabStock Ledger Entry`
			where item_code=%s and batch_no=%s""",
			(self.item_code, self.batch_no))[0][0])

		picked_qty = flt(frappe.db.sql("""select sum(qty - (delivered_qty + wastage_qty))
			from `tabPick List Item` as pli
			JOIN `tabPick List` as pl on pl.name = pli.parent
			where pli.item_code=%s and pli.batch_no=%s and pl.docstatus = 1""",
			(self.item_code, self.batch_no))[0][0])

		if batch_bal_after_transaction_without_warehouse - picked_qty < 0:
			frappe.throw(_("Stock balance after Picked Qty in Batch {0} will become negative {1} for Item {2}")
				.format(self.batch_no, (batch_bal_after_transaction - picked_qty), self.item_code))
