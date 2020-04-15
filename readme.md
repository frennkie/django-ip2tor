
pylightning <- Christian Decker (for lightningd (=c-lightning?!))

https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
https://github.com/ElementsProject/lightning/tree/master/contrib/pylightning

switch in sites (in APPs and Site_id)


migrate

createsuperuser --username admin --email admin@example.com

-> go to Sites and change the initial domain name (and display name)

-> go to user and create operator (and add to "operators" group)

-> go to Hosts and create your first host



lnnode requires Redis (used to recudes external calls (e.g. getinfo) and improve performance)


ToDo

- Heartbeat / Check
- Maybe: validate/clean/save that models are only set to things the user owns
- AGBs/ToS



https://github.com/jazzband/django-taggit/commit/90c7224018c941b9a260c8e8bed166536f5870df

../jobs.sh

daphne django_ip2tor.asgi:application --port 8001 --proxy-headers