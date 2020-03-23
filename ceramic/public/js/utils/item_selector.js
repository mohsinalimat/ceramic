ItemSelector = Class.extend({
	init: function (opts) {
		$.extend(this, opts);
		this.setup();
	},

	setup: function(){
		this.set_variables();
		this.make_dialog();
	},

	set_variables: function() {
		this.package_data = [];
	},

	make_dialog: function(){
		let me = this;

		let fields = [
			{
				label: __('Item Code'),
				fieldtype:'Link',
				fieldname: 'item_code',
				options: 'Item',
				read_only: 0,
				reqd: 1,
				get_query: function(){
					let items = [...new Set((me.frm.doc.locations).map(function(i){return i.item_code}))]
					return {
						filters: {
							"item_code": ['in', items]
						}
					}
				},
				change: function(){
					let filters = {'item_code': this.layout.get_value('item_code')};
					me.get_items(filters)
				}
			},

			{fieldtype:'Column Break'},

			{
				label: __('Sales Order'),
				fieldtype:'Link',
				fieldname: 'sales_order',
				options: 'Sales Order',
				reqd: 1,
				get_query: function(){
					let item = this.cur_dialog.fields_dict.item_code.value
					let sales_order = [...new Set((me.frm.doc.locations).map(function(i){if (i.item_code === item){return i.sales_order}}))]
					return {
						filters: {
							"name": ['in', sales_order]
						}
					}
				},
				change: function() {
					let item = this.layout.get_value('item_code');

					let sales_order = this.layout.get_value('sales_order');

					(me.frm.doc.locations).map(function(i){
						if (i.item_code === item && i.sales_order === sales_order){
							this.cur_dialog.set_value('sales_order_item', i.sales_order_item);
							// this.set_package_data();
						}
					});
				}
			},
			{
				label: __('Sales Order Item'),
				fieldtype:'Data',
				fieldname: 'sales_order_item',
				reqd: 0,
				read_only: 1,
				hidden: 1,
				change: function () {
					let item = this.layout.get_value('item_code');
					let sales_order = this.layout.get_value('sales_order');
					let sales_order_item = this.layout.get_value('sales_order_item');
					let total_qty = 0;
					(me.frm.doc.locations).map(function(i){
						if (i.item_code === item && i.sales_order === sales_order && i.sales_order_item === sales_order_item){
							total_qty = total_qty + i.qty
							this.cur_dialog.set_value('so_qty', total_qty);
						}
					});
				}
			},
			{ fieldtype: 'Section Break', label: __('Quantity') },
			{
				label: __('Sales Order Qty'),
				fieldtype:'Float',
				fieldname: 'so_qty',
				reqd: 0,
				default: 0.0,
				read_only: 1,
			},
			{fieldtype:'Column Break'},
			{
				label: __('Picked Qty'),
				fieldtype:'Float',
				fieldname: 'picked_qty',
				default: 0.0,
				reqd: 0,
				read_only: 1,
			},
		]
		
		fields = fields.concat(this.get_package_fields());

		this.dialog = new frappe.ui.Dialog({
			title: __("Add Items"),
			fields: fields,
		});
		
		let filters = {
			'item_code': this.item_code,
		}

		this.get_items(filters);

		this.dialog.set_primary_action(__("Add"), function(){
			me.values = me.dialog.get_values();

			let picked_qty = me.values.picked_qty
			let so_qty = me.values.so_qty

			if (so_qty === picked_qty){
				me.set_packages_in_frm();
				me.dialog.hide();
			} else {
				frappe.msgprint("Picked Qty and Sales Order Qty Are not equal")
			}
		});

		let $package_wrapper = this.get_package_wrapper();

		$($package_wrapper).find('.grid-remove-rows').hide();
		$($package_wrapper).find('.grid-add-row').hide();

		this.dialog.show();

		this.bind_events();
	},

	get_package_fields: function(){
		let me = this;

		return [
			{ fieldtype: 'Section Break', label: __('Items') },
			{
				fieldname: 'packages',
				label:'',
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
						'in_list_view': 1,
					},
					{
						'label': 'Picked Qty',
						'fieldtype': 'Float',
						'fieldname': 'picked_qty',
						'read_only': 0,
						'in_list_view': 1,
						change: function(){
							me.cal_picked_qty();
						}
					},
					{
						'label': 'Avalilable Qty',
						'fieldtype': 'Float',
						'fieldname': 'available_qty',
						'read_only': 1,
						'in_list_view': 1,
					}
				],
				
				in_place_edit: true,
				// data: this.data,
				get_data: function(){
					return ;
				},
				
			}
		]
	},

	get_package_wrapper: function(){
		return this.dialog.get_field('packages').$wrapper;
	},

	get_selected_packages: function() {
		let me = this;
		let selected_packages = [];
		let $package_wrapper = this.get_package_wrapper();
		let packages = this.dialog.get_value('packages');

		$.each($package_wrapper.find('.form-grid > .grid-body > .rows > .grid-row'), function (idx, row) {
			var pkg = $(row).find('.grid-row-check:checkbox');

			let package = packages[idx];
			
			if($(pkg).is(':checked')){
				selected_packages.push(package);
				package.__checked = 1;
			} else {
				package.__checked = 0;
			}
		});

		return selected_packages;
	},
	
	bind_events: function($wrapper) {
		let me = this;

		let $package_wrapper = me.get_package_wrapper();

		$package_wrapper.on('click', '.grid-row-check:checkbox', (e) => {
			me.cal_picked_qty();
		})

	},

	cal_picked_qty: function(){
		let me = this;
		
		let packages = me.dialog.get_value('packages');
		let so_qty = me.dialog.fields_dict.so_qty.value
		let selected_packages = me.get_selected_packages();
		let picked_qty = frappe.utils.sum((selected_packages || []).map(row => row.picked_qty));

		me.dialog.set_value('picked_qty', picked_qty);
	},

	set_packages_in_frm: function () {
		let me = this;
		let selected_packages = this.get_selected_packages();
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

		(selected_packages || []).forEach(function(d){
			d.__checked = 0;
			var locations = me.frm.add_child('locations');
			console.log(locations.doctype)
			frappe.model.set_value(locations.doctype, locations.name, 'item_code', d.item_code);
			frappe.model.set_value(locations.doctype, locations.name, 'warehouse', d.warehouse);
			frappe.model.set_value(locations.doctype, locations.name, 'qty', d.picked_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'picked_qty', d.picked_qty);
			frappe.model.set_value(locations.doctype, locations.name, 'sales_order', sales_order);
			frappe.model.set_value(locations.doctype, locations.name, 'sales_order_item', sales_order_item);
			frappe.model.set_value(locations.doctype, locations.name, 'batch_no', d.batch_no);
		})

		me.frm.doc.locations.forEach(function(d, idx){
			frappe.model.set_value(d.doctype, d.name, 'idx', idx + 1);
		});

		refresh_field('locations');
	},

	get_package_filters: function(){
		let me = this;
		let values = this.dialog.get_values();
		let filters = {
			'warehouse': this.warehouse
		};

		if(!values.item_code){
			frappe.throw(__("Please set Item Code!"))
		} else {
			filters['item_code'] = values.item_code;
		}

		if(!values.merge){
			frappe.throw(__("Please set Merge!"))
		} else {
			filters['merge'] = values.merge;
		}

		if(values.grade){
			filters['grade'] = values.grade;
		}

		if(values.paper_tube){
			filters['paper_tube'] = values.paper_tube;
		}

		if(values.spools){
			filters['spools'] = values.spools;
		}

		if(values.package){
			filters['package'] = values.package;
		}

		return filters;
	},

	set_filtered_package_data: function() {
		let me = this;
		let filters = this.get_package_filters();
		let packages = this.dialog.fields_dict.packages;

		let data = this.package_data.filter(function(row){
			let flag = 1;

			$.each(filters, function(key, value){
				if(row[key].toString().indexOf(value.toString()) > -1 && flag){
					flag = 1;
				} else { flag = 0 }

				if(flag == 0) {
					return false;
				}
			})

			return flag == 1;
		});

		let filtered_data = me.get_remove_selected_packages(data);

		// packages.grid.df.data = data;
		packages.grid.df.data = filtered_data;
		packages.grid.refresh();
	},

	get_items: function(filters){
		let me = this;
		let packages = this.dialog.fields_dict.packages;

		if(!filters['item_code']){
			packages.grid.df.data = [];
			packages.grid.refresh();
			return;
		}

		filters['company'] = me.frm.doc.company;

		frappe.call({
			method: "ceramic.ceramic.doc_events.pick_list.get_items",
			freeze: true,
			args: {
				'filters': filters,
			},
			callback: function(r){
				packages.grid.df.data = r.message;
				packages.grid.refresh();
				me.set_package_data();
			},
		});
	},

	set_package_data: function() {
		let me = this;
		this.package_data = this.dialog.get_value('packages');
	},

	get_remove_selected_packages: function(data) {
		let me = this;
		let remove_selected = this.dialog.get_value('remove_selected');

		if(!remove_selected){
			return data;
		} else {
			let filtered_data = data.filter(function(row) {
				return !me.package_exists(row.package);
			});

			return filtered_data;
		}
	},

	package_exists: function(package){
		const packages = this.frm.doc.packages.map(data => data.package);
		return (packages && in_list(packages, package)) ? true : false;
	},
});
