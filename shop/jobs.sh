#!/bin/bash
# jobs.sh: Execute background tasks:
#  - processing of new (=initial) purchase orders (by creating an invoice)
#  - processing of new (=initial) invoice (by actually creating the invoice on a Lightning Node
#  - processing of unpaid lightning invoices (check for payment)

sleep_time=10

while :; do
  echo "Job: Process Purchase Orders (initial)"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_pos_initial
  sleep 1

  echo "Job: Process Lightning Invoices (initial)"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_lni_initial
  sleep 1

  echo "Job: Process Lightning Invoices (unpaid)"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_lni_unpaid

  echo "Sleeping for ${sleep_time} seconds.."
  sleep ${sleep_time}

done
