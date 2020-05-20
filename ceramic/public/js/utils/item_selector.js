ItemSelector = Class.extend({
	init: function (opts) {
		$.extend(this, opts);
		this.setup();
	},

	setup: function(){
		this.item_locations_data = []
		this.make_dialog();
	},
	
	make_dialog: function(){
		let me = this;
		this.data = [];

		let fields = 
		[
			{
				label: __('Item Code'),
				fieldtype:'Link',
				fieldname: 'item_code',
				options: 'Item',
				read_only: 1,
				reqd: 1,
				default: me.item_code,
			},

			{fieldtype:'Column Break'},

			{
				label: __('Sales Order'),
				fieldtype:'Link',
				fieldname: 'sales_order',
				options: 'Sales Order',
				reqd: 1,
				read_only: 1,
				default: me.sales_order
			},
			{
				label: __('Sales Order Item'),
				fieldtype:'Data',
				fieldname: 'sales_order_item',
				reqd: 0,
				read_only: 1,
				hidden: 1,
				default: me.sales_order_item
			},
			{ fieldtype: 'Section Break', label: __('Quantity') },
			{
				label: __('Sales Order Qty'),
				fieldtype:'Float',
				fieldname: 'so_qty',
				reqd: 0,
				default: me.so_qty,
				read_only: 0,
				change: function(){
					let previously_picked = this.layout.get_value('previously_picked') || 0;
					let picked_qty = this.layout.get_value('picked_qty') || 0;
					let so_qty = this.layout.get_value('so_qty') || 0;
					cur_dialog.set_value('remaining_to_pick', (so_qty - previously_picked - picked_qty));
				}
			},
			{
				label: __('Previously Picked'),
				fieldtype:'Float',
				fieldname: 'previously_picked',
				reqd: 0,
				default: me.picked_qty,
				read_only: 1,
				hidden: 1,
			},
			{
				label: __('Sales Order Real Qty'),
				fieldtype:'Float',
				fieldname: 'so_real_qty',
				reqd: 0,
				default: me.so_real_qty,
				read_only: 0,
			},
			{fieldtype:'Column Break'},
			{
				label: __('Picked Qty'),
				fieldtype:'Float',
				fieldname: 'picked_qty',
				default: '0',
				reqd: 0,
				read_only: 1,
				change: function(){
					let previously_picked = this.layout.get_value('previously_picked') || 0;
					let picked_qty = this.layout.get_value('picked_qty') || 0;
					let so_qty = this.layout.get_value('so_qty') || 0;
					cur_dialog.set_value('remaining_to_pick', (so_qty - previously_picked - picked_qty));
				}
			},
			{
				label: __('Remaining to Pick Qty'),
				fieldtype:'Float',
				fieldname: 'remaining_to_pick',
				default: me.remaining_to_pick,
				reqd: 0,
				read_only: 1,
				change: function(){
					me.set_item_qty()
				}
			}
		]

		fields = fields.concat(this.get_item_fields());

		me.dialog = new frappe.ui.Dialog({
			title: __("Add Items"),
			fields: fields,
		});

		me.dialog.set_primary_action(__("Add"), function(){
			me.values = me.dialog.get_values();

			let picked_qty = me.values.picked_qty + me.picked_qty
			let so_qty = me.values.so_qty

			if (so_qty >= picked_qty){
				me.set_item_locations_in_frm();
				me.dialog.hide();
			} else {
				frappe.msgprint("Picked Qty should be less than " + (so_qty - me.picked_qty))
			}
		});

		let $package_wrapper = this.get_item_location_wrapper();

		$($package_wrapper).find('.grid-remove-rows .grid-delete-rows').click(function (event) {
			dialog(this);
			event.preventDefault();
			event.stopPropagation();
			return false;
	 });
		// $($package_wrapper).find('.grid-add-row').hide();

		me.dialog.show();
		let filters = {'item_code': me.item_code};
		me.get_items(filters);

		this.bind_events();
	},
	get_items: function(filters) {
		let me = this;
		let item_locations = me.dialog.fields_dict.item_locations;

		if(!filters['item_code']){
			item_locations.grid.df.data = [];
			item_locations.grid.refresh();
			return;
		}

		filters['company'] = me.company;
		filters['to_pick_qty'] = me.remaining_to_pick

		frappe.call({
			method: "ceramic.ceramic.doc_events.pick_list.get_items",
			freeze: true,
			args: {
				'filters': filters,
			},
			callback: function(r){
				// me.dialog.set_value('item_locations', )
				// console.log(r.message)
				item_locations.grid.df.data = []
				r.message.forEach(value => {
					me.frm.doc.available_qty.forEach(element => {
						if (value.batch_no == element.batch_no){
							value.available_qty = value.available_qty - (element.picked_in_current || 0)
						}
					});
					if (me.batch_no && value.batch_no == me.batch_no){
						value.available_qty = value.available_qty + me.qty
					}
					value.to_pick_qty = Math.min(value.to_pick_qty, value.available_qty)
					item_locations.grid.df.data.push(value)
				});

				// item_locations.grid.df.data = r.message;
				item_locations.grid.refresh();
				// me.set_item_location_data();
			},
		});
	},
	get_item_fields: function(){
		let me = this;

		return [
			{fieldtype:'Section Break', label: __('Item Location Details')},
			{
				label: __("Item"),
				fieldname: 'item_locations',
				fieldtype: "Table",
				read_only: 0,
				fields:[
					{
						'label': 'Item Code',
						'fieldtype': 'Link',
						'fieldname': 'item_code',
						'options': 'Item',
						'read_only': 1,
					},
					{
						'label': 'Item Name',
						'fieldtype': 'Data',
						'fieldname': 'item_name',
						'read_only': 1,
					},
					{
						'label': 'Warehouse',
						'fieldtype': 'Link',
						'fieldname': 'warehouse',
						'options': 'Warehouse',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Batch No',
						'fieldtype': 'Link',
						'fieldname': 'batch_no',
						'options': 'Batch',
						'read_only': 1,
						'in_list_view': 0,
					},
					{
						'label': 'Lot No',
						'fieldtype': 'Data',
						'fieldname': 'lot_no',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'To Pick',
						'fieldtype': 'Float',
						'fieldname': 'to_pick_qty',
						'in_list_view': 1,
						change: function(){
							me.cal_picked_qty();
						}
					},					
					// {
					// 	'label': 'Avalilable to Pick',
					// 	'fieldtype': 'Float',
					// 	'fieldname': 'to_pick_qty',
					// 	'read_only': 0,
					// 	'in_list_view': 1,
					// 	// change: function(){
					// 	// 	me.cal_picked_qty();
					// 	// }
					// },
					{
						'label': 'Avalilable Qty',
						'fieldtype': 'Float',
						'fieldname': 'available_qty',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Actual Qty',
						'fieldtype': 'Float',
						'fieldname': 'actual_qty',
						'read_only': 1,
						'in_list_view': 1,
					},
					{
						'label': 'Picked Qty',
						'fieldtype': 'Float',
						'fieldname': 'picked_qty',
						'read_only': 1,
						'in_list_view': 0,
					},
					
				],
				in_place_edit: false,
				// data: this.data,
				get_data: function() {
					return this.data;
				},
			}
		];
	},
	cal_picked_qty: function(){
		let me = this;

		let selected_item_locations = me.get_selected_item_locations();
		let picked_qty = frappe.utils.sum((selected_item_locations || []).map(row => row.to_pick_qty));
		me.dialog.set_value('picked_qty', picked_qty);
		
	},
	set_item_location_data: function(){
		let me = this;
		me.item_locations_data = me.dialog.get_value('item_locations');
	},
	bind_events: function($wrapper) {
		let me = this;

		let $item_location_wrapper = me.get_item_location_wrapper();

		$item_location_wrapper.on('click', '.grid-row-check:checkbox', (e) => {
			me.cal_picked_qty();
		})

	},
	get_item_location_wrapper: function(){
		let me = this;
		return me.dialog.get_field('item_locations').$wrapper;
	},
	get_selected_item_locations: function() {
		let me = this;
		let selected_item_locations = [];
		let $item_location_wrapper = this.get_item_location_wrapper();
		let item_locations = me.dialog.get_value('item_locations');

		$.each($item_location_wrapper.find('.form-grid > .grid-body > .rows > .grid-row'), function (idx, row) {
			var pkg = $(row).find('.grid-row-check:checkbox');

			let item_location = item_locations[idx];
			
			if($(pkg).is(':checked')){
				selected_item_locations.push(item_location);
				item_location.__checked = 1;
			} else {
				item_location.__checked = 0;
			}
		});

		return selected_item_locations;
	},
	set_item_qty: function() {
		let me = this;
		let selected_item_locations = [];
		let $item_location_wrapper = this.get_item_location_wrapper();
		let item_locations = me.dialog.get_value('item_locations');
		let remaining_to_pick = me.dialog.get_value('remaining_to_pick');

		$.each($item_location_wrapper.find('.form-grid > .grid-body > .rows > .grid-row'), function (idx, row) {
			var pkg = $(row).find('.grid-row-check:checkbox');

			let item_location = item_locations[idx];
			
			if($(pkg).is(':checked')){
				selected_item_locations.push(item_location);
				item_location.__checked = 1;
			} else {
				item_location.__checked = 0;
				console.log(remaining_to_pick)
				item_location.to_pick_qty = Math.min((remaining_to_pick || 0), (item_location.to_pick_qty || 0))
			}
		});
		let item_locations2 = me.dialog.fields_dict.item_locations;
		item_locations2.grid.refresh();

		// return selected_item_locations;
	},
	set_item_locations_in_frm: function () {
		let me = this;
		let selected_item_locations = this.get_selected_item_locations();
		let item_code = me.values.item_code
		let sales_order = me.values.sales_order
		let sales_order_item = me.values.sales_order_item

		var loc = [];

		me.frm.doc.locations.forEach(function(value, idx){
			if (value.sales_order_item != sales_order_item){
				loc.push(value)
			}
		});
		me.frm.doc.locations = loc;

		(selected_item_locations || []).forEach(function(d){
			d.__checked = 0;
			var locations = me.frm.add_child('locations');
			frappe.model.set_value(locations.doctype, locations.name, 'item_code', d.item_code);
			frappe.model.set_value(locations.doctype, locations.name, 'customer', me.customer);
			frappe.model.set_value(locations.doctype, locations.name, 'so_qty', me.values.so_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'so_real_qty', me.values.so_real_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'delivery_date', me.delivery_date);
			frappe.model.set_value(locations.doctype, locations.name, 'date', me.date);
			frappe.model.set_value(locations.doctype, locations.name, 'warehouse', d.warehouse);
			frappe.model.set_value(locations.doctype, locations.name, 'qty', d.to_pick_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'picked_qty', me.picked_qty || 0);
			frappe.model.set_value(locations.doctype, locations.name, 'available_qty', d.available_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'actual_qty', d.actual_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'sales_order', sales_order);
			frappe.model.set_value(locations.doctype, locations.name, 'sales_order_item', sales_order_item);
			frappe.model.set_value(locations.doctype, locations.name, 'batch_no', d.batch_no);
		})

		me.frm.doc.locations.forEach(function(d, idx){
			frappe.model.set_value(d.doctype, d.name, 'idx', idx + 1);
		});

		refresh_field('locations');
	},
});