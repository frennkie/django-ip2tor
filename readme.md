# Intro

... TODO ...


## Installation

Please be aware that the IP2TOR consist of two separate server roles. 

There is the `Shop` and there are `Hosts` (or `Bridge Hosts`). The `Shop` is an application 
based on the Python Django Web Framework that provides a management interface to register 
multiple operator accounts and also Bitcoin Lightning wallets/nodes. Within the `Shop` it 
is also possible to register multiple `Hosts` that will take over the role of actually 
hosting the IP to TOR (or more precisely TCP-Port to TOR Hidden Service).

### Installing a Host

First make sure that TOR is installed and configured/enabled. 

Secondly install any other dependencies. Currently these are
 
* `jq`
* `socat`

Thirdly you need to register the `Hosts` in at least one `Shop` first to get the credentials
that are needed to retrieve the specific information for this `Host` from the `Shop` database
and to make updates (e.g. mark a `Bridge` as active).

Don't forget to allow the TCP port ranges on your firewall (both local and network/cloud based).

```
cd /tmp
git clone https://github.com/frennkie/django-ip2tor/
cd django-ip2tor
sudo install -m 0755 -o root -g root -t /usr/local/bin scripts/ip2tor_host.sh
sudo install -m 0755 -o root -g root -t /usr/local/bin scripts/ip2torc.sh
sudo install -m 0644 -o root -g root -t /etc/systemd/system contrib/ip2tor-host.service
```

Now create the configuration file (`sudo vi /etc/ip2tor.conf`) and enter the credentials - e.g. like this:

```
IP2TOR_SHOP_URL=https://ip2tor.fulmo.org
IP2TOR_HOST_ID=58b61c0b-0a00-0b00-0c00-0d0000000000
IP2TOR_HOST_TOKEN=5eceb05d00000000000000000000000000000000
```

Finally reload systemd, enable and start the service.

```
sudo systemctl daemon-reload
sudo systemctl enable ip2tor-host.service
sudo systemctl start ip2tor-host.service
```

Check the logs using `sudo journalctl --follow -u ip2tor-host`

Two useful commands to see what's going on are these:

`ip2torc.sh list` shows a list of the IP2TOR systemd services that are active on this `Host`. 

```
/usr/local/bin/ip2torc.sh list
# Bridges (PORT|TARGET|STATUS)
# ============================
20159|answerszuvs3gg2l64e6hmnryudl5zgrmwm3vh65hzszdghblddvfiqd.onion:80|active (running) since Fri 2020-07-03 20:43:43 GMT; 12h ago
```

`ip2tor_host.sh list` retrieves a current list from the `Shop` with details which Bridges should 
be hosted on this `Host` and in which status they are. 

```
/usr/local/bin/ip2tor_host.sh list
20159|0059bdb1-0a00-0b00-0c00-0000000000000000|A|answerszuvs3gg2l64e6hmnryudl5zgrmwm3vh65hzszdghblddvfiqd.onion:80

```


## Shop

About...

### Requirements

The intention is to support (and actively test for) common target platforms:

- CentOS 8+ (amd64)
- Debian 10+ (amd64 and arm)
- Ubuntu LTS (amd64) releases starting with 18.04

The `Shop` setup requires the following services:

- nginx, which acts as a reverse proxy and serves static files (assets like .css, .js..)
- redis, which is used as a cache and a message broker
- postgres, as the database (for development, tests and in really small environments sqlite3 
can be used)   


The actual application is written in the Python web framework `Django` and all code must currently
be be compatible with Python 3.6+. The `Celery` toolset is used for asynchronous/background 
processing of jobs and to schedule the executing of periodic events (a substitute for cron).


### Installing the Shop 

#### System packages

```
sudo apt install nginx redis
```

Setup nginx (see contrib/shop.ip2t.org.conf)


#### Python etc.

```
apt-get install python3-venv

sudo mkdir -p /var/www/sites/site_django_ip2tor

sudo chown -R www-data:www-data /var/www/sites/site_django_ip2tor

sudo -H -u www-data bash

cd /var/www/sites/site_django_ip2tor

/usr/bin/python3 -m venv /var/www/sites/site_django_ip2tor/venv
source /var/www/sites/site_django_ip2tor/venv/bin/activate
python -m pip install --upgrade pip

git clone https://github.com/frennkie/django-ip2tor
python -m pip install --upgrade pip 
python -m pip install --upgrade setuptools
python -m pip install --upgrade -r requirements.txt
python manage.py collectstatic
python manage.py migrate

python manage.py createsuperuser --username admin --email admin@example.com

```

Limit access rights to base and media directory

```
sudo chmod 770 /var/www/sites/site_django_ip2tor/django_ip2tor
sudo chmod 770 /var/www/sites/site_django_ip2tor/media
```


Setup systemd service for Django web application

```
sudo install -m 0644 -o root -g root -t /etc/systemd/system contrib/ip2tor-web.service
sudo systemctl daemon-reload
sudo systemctl enable ip2tor-web.service
sudo systemctl start ip2tor-web.service
```


Celery

```
sudo useradd celery --system -d /var/lib/celery -b /bin/sh

sudo usermod -a -G www-data celery
# or
sudo usermod -a -G nginx celery

cat <<EOF | sudo tee "/etc/tmpfiles.d/celery.conf" >/dev/null
d /run/celery 0755 celery celery -
d /var/log/celery 0755 celery celery -
EOF
sudo systemd-tmpfiles --create --remove

sudo install -m 0644 -o root -g root -t /etc/systemd/system contrib/ip2tor-beat.service
sudo install -m 0644 -o root -g root -t /etc/systemd/system contrib/ip2tor-worker.service
sudo install -m 0644 -o root -g root -t /etc/ contrib/celery.conf
```

Make sure that the `celery` user has write access to the database. If you use SQlite then run 
the following (when using Postgres you only need to ensure that the settings.py with the 
credentials is readable the `celery`):

```
if [ -f "/var/www/sites/site_django_ip2tor/django_ip2tor/db.sqlite3" ]; then
  sudo chmod 664 /var/www/sites/site_django_ip2tor/django_ip2tor/db.sqlite3
fi
``` 

Enable and start celery

```
sudo systemctl daemon-reload
sudo systemctl enable ip2tor-beat.service
sudo systemctl enable ip2tor-worker.service
sudo systemctl start ip2tor-beat.service
sudo systemctl start ip2tor-worker.service
```


Run celery manually (for debug/dev/testing)

```
celery.exe -A django_ip2tor worker -c 2 -l info --pool=solo  # dev on Windows
celery -A django_ip2tor worker -l info
celery -A django_ip2tor beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```


CentOS Stuff

```
setsebool -P httpd_can_network_connect 1
chcon -Rt httpd_sys_content_t /var/www/
```
 
yum install -y libpq-devel


python -m pip install --upgrade psycopg2
or
python -m pip uninstall psycopg2-binary


#### Initial setup

-> go to Sites and change the initial domain name (and display name)

-> go to user and create operator (and add to "operators" group)

-> go to Hosts and create your first host






## Loose Notes

pylightning <- Christian Decker (for lightningd (=c-lightning?!))

https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md
https://github.com/ElementsProject/lightning/tree/master/contrib/pylightning

switch on sites (in APPs and Site_id)

`lnnode` requires Redis (used to reduces external calls (e.g. getinfo) and improve performance)

ToDo

- Heartbeat / Check
- Maybe: validate/clean/save that models are only set to things the user owns
- AGBs/ToS
- loaddata did't work (caused by signal activity) - check again now that celery tasks are used.


https://github.com/jazzband/django-taggit/commit/90c7224018c941b9a260c8e8bed166536f5870df


pymacaroons

https://gist.github.com/htp/fbce19069187ec1cc486b594104f01d0


python manage.py migrate --settings django_ip2tor.settings_prod

Run on host to monitor

```
while :
do
  ./tor2ipc.sh list
  sleep 10
done
```