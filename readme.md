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
sudo apt install -y nginx redis git
# OR
sudo yum install -y nginx redis git
```

Setup nginx (see contrib/shop.ip2t.org.conf)


#### User account for service

Create a dedicated user account which is used to run the needed services. Celery needs this 
account to have a shell (therefore /usr/sbin/nologin does not work).

```
sudo useradd ip2tor --comment "IP2Tor Services" --home /home/ip2tor --shell /bin/bash
sudo chmod 750 /home/ip2tor
```

Add the new `ip2tor` group to the web user

```
if getent passwd www-data > /dev/null 2&>1 ; then
  sudo usermod -a -G ip2tor www-data
elif getent passwd nginx > /dev/null 2&>1 ; then
  sudo usermod -a -G ip2tor nginx
else
  echo "ERR: Found neither www-data nor nginx user"
fi
```



#### Python etc.

Install venv

```
sudo apt install -y python3-venv
# OR 
sudo yum install -y python3-virtualenv
```

Change to service user and install + update virtual python environment

```
sudo su - ip2tor
/usr/bin/python3 -m venv /home/ip2tor/venv
source /home/ip2tor/venv/bin/activate
python -m pip install --upgrade pip setuptools
```

Get the code (either last release as zip or latest master) from Github

```
curl -o django-ip2tor.zip https://codeload.github.com/frennkie/django-ip2tor/zip/master
unzip django-ip2tor.zip
mv django-ip2tor-master django-ip2tor
rm -f django-ip2tor.zip
# OR
git clone https://github.com/frennkie/django-ip2tor
```

Install python dependencies

```
cd django-ip2tor
python -m pip install --upgrade -r requirements.txt
````

Setup Environment (e.g. SECRET_KEY!)

```
/home/ip2tor/venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
cp example.env .env
vi .env  # update stuff
```

Run django setup jobs

```
python manage.py collectstatic
mkdir /home/ip2tor/media
python manage.py makemigrations  # should normally not create new migrations!
python manage.py migrate
python manage.py createsuperuser --username admin --email admin@example.com
```

Limit access rights to base and media directory

```
sudo chmod 700 /home/ip2tor/django-ip2tor
sudo chmod 750 /home/ip2tor/media
sudo chmod 750 /home/ip2tor/static
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
cat <<EOF | sudo tee "/etc/tmpfiles.d/celery.conf" >/dev/null
d /run/celery 0755 ip2tor ip2tor -
d /var/log/celery 0755 ip2tor ip2tor -
EOF
sudo systemd-tmpfiles --create --remove

sudo install -m 0644 -o root -g root -t /etc/systemd/system contrib/ip2tor-beat.service
sudo install -m 0644 -o root -g root -t /etc/systemd/system contrib/ip2tor-worker.service
sudo install -m 0644 -o root -g root -t /etc/ contrib/celery.conf
```

Enable and start celery

```
sudo systemctl daemon-reload
sudo systemctl enable ip2tor-beat.service
sudo systemctl enable ip2tor-worker.service
sudo systemctl start ip2tor-beat.service
sudo systemctl start ip2tor-worker.service
```

CentOS Stuff

```
setsebool -P httpd_can_network_connect 1
chcon -Rt httpd_sys_content_t /home/ip2tor/static
chcon -Rt httpd_sys_content_t /home/ip2tor/media
```
 
Postgres on CentOS

```
yum install -y libpq-devel

python -m pip install --upgrade psycopg2
# OR or
python -m pip uninstall psycopg2-binary
```


#### Initial setup

-> go to Sites and change the initial domain name (and display name)

-> go to user and create operator (and add to "operators" group)

-> go to Hosts and create your first host



### Troubleshooting

Run celery manually (for debug/dev/testing)

```
celery.exe -A django_ip2tor worker -c 2 -l info --pool=solo  # dev on Windows
celery -A django_ip2tor worker -l info
celery -A django_ip2tor beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```


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


python manage.py migrate

Run on host to monitor

```
while :
do
  ./tor2ipc.sh list
  sleep 10
done
```
