from __future__ import unicode_literals
from frappe import _

def get_data(data):
	data['non_standard_fieldnames'] = {
		'Journal Entry': 'reference_name',
		'Payment Entry': 'reference_name',
		'Payment Request': 'reference_name',
		'Sales Invoice': 'return_against',
		'Auto Repeat': 'reference_document',
	}

	data['internal_links'] ={
		'Sales Order': ['items', 'sales_order'],
		'Delivery Note': ['items', 'delivery_note']
	}

	data['transactions'] = [
		{
			'label': _('Payment'),
			'items': ['Payment Entry', 'Payment Request', 'Journal Entry']
		},
		{
			'label': _('Reference'),
			'items': ['Delivery Note', 'Sales Order']
		},
		{
			'label': _('Returns'),
			'items': ['Sales Invoice']
		},
		{
			'label': _('Subscription'),
			'items': ['Auto Repeat']
		},
	]

	return data