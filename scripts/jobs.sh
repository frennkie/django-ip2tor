#!/bin/bash
# jobs.sh: Execute background tasks:
#  - processing of new (=initial) purchase orders (by creating an invoice)
#  - processing of new (=initial) invoice (by actually creating the invoice on a Lightning Node
#  - processing of unpaid lightning invoices (check for payment)
#  - processing of deleted tor bridges (delete from db if old than N days)
#  - processing of initial tor bridges (change state to delete if never paid)
#  - processing of active tor bridges (change state to suspended if expired)

sleep_time=2

while :
do
  echo "Job: Process Purchase Orders (initial)"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_pos_initial --settings django_ip2tor.settings_prod
  sleep 1

  echo "Job: Process Lightning Invoices (initial)"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_lni_initial --settings django_ip2tor.settings_prod
  sleep 1

  echo "Job: Process Lightning Invoices (unpaid)"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_lni_unpaid --settings django_ip2tor.settings_prod
  sleep 1

  echo "Job: Process Tor Bridges"
  /var/www/sites/site_django_ip2tor/venv/bin/python /var/www/sites/site_django_ip2tor/django_ip2tor/manage.py process_tor_bridges --settings django_ip2tor.settings_prod

  echo "Sleeping for ${sleep_time} seconds.."
  sleep ${sleep_time}

done
