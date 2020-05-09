
## Quick Start


### System packages

```
sudo apt install nginx redis
```

Setup nginx (see contrib/shop.ip2t.org.conf)


### Python etc.

```
apt-get install python3-venv

sudo mkdir -p /var/www/sites/site_django_ip2tor

sudo chown -R www-data:www-data /var/www/sites/site_django_ip2tor

sudo -H -u www-data bash

cd /var/www/sites/site_django_ip2tor

/usr/bin/python3 -m venv /var/www/sites/site_django_ip2tor/venv
source /var/www/sites/site_django_ip2tor/venv/bin/activate
python -m pip install --upgrade pip

git clone https://github.com/frennkie/ip2tor_shop
python -m pip install --upgrade -r requirements.txt
python manage.py collectstatic
python manage.py migrate

createsuperuser --username admin --email admin@example.com


daphne django_ip2tor.asgi:application --port 8001 --proxy-headers

```

### Run "worker" - open another terminal (tmux):

```
/var/www/sites/site_django_ip2tor/django_ip2tor/scripts/jobs.sh
```


### Initial setup

-> go to Sites and change the initial domain name (and display name)

-> go to user and create operator (and add to "operators" group)

-> go to Hosts and create your first host





pylightning <- Christian Decker (for lightningd (=c-lightning?!))

https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
https://github.com/ElementsProject/lightning/tree/master/contrib/pylightning

switch on sites (in APPs and Site_id)

`lnnode` requires Redis (used to reduces external calls (e.g. getinfo) and improve performance)


ToDo

- Heartbeat / Check
- Maybe: validate/clean/save that models are only set to things the user owns
- AGBs/ToS

https://github.com/jazzband/django-taggit/commit/90c7224018c941b9a260c8e8bed166536f5870df


pymacaroons


https://gist.github.com/htp/fbce19069187ec1cc486b594104f01d0
