
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
python -m pip install --upgrade pip 
python -m pip install --upgrade setuptools
python -m pip install --upgrade -r requirements.txt
python manage.py collectstatic
python manage.py migrate

python manage.py createsuperuser --username admin --email admin@example.com


daphne django_ip2tor.asgi:application --port 8001 --proxy-headers

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


python manage.py migrate --settings django_ip2tor.settings_prod

loaddata doesn't work



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

Run on host to monitor

```
while :
do
  ./tor2ipc.sh list
  sleep 10
done
```

Run on host to add bridges

```
while :
do
  ./host_cli.sh pending
  sleep 10
done
```

sudo install -m 0755 -o root -g root -t /usr/local/bin scripts/ip2tor_host.sh
sudo install -m 0755 -o root -g root -t /usr/local/bin scripts/ip2torc.sh
sudo vi /etc/ip2tor.conf

sudo cp contrib/ip2tor-host.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ip2tor-host
sudo systemctl start ip2tor-host



## Installing

Please be aware that the IP2TOR consist of two separate server roles. 

There is the `Shop` and there are `Hosts` (or `Bridge Hosts`). The `Shop` is an application 
based on the Python Django Web Framework that provides a management interface to register 
multiple operator accounts and also Bitcoin Lightning wallets/nodes. Within the `Shop` it 
is also possible to register multiple `Hosts` that will take over the role of actually 
hosting the IP to TOR (or more precisely TCP-Port to TOR Hidden Service).

### Installation on a Host

First make sure that TOR is installed and configured/enabled. 

Secondly install any other dependencies. Currently the only one is: `jq`.

Thirdly you need to register the `Hosts` in at least one `Shop` first to get the credentials
that are needed to retrieve the specific information for this `Host` from the `Shop` database
and to make updates (e.g. mark a `Bridge` as active).
 

```
cd /tmp
git clone https://github.com/frennkie/django-ip2tor/
cd django-ip2tor
sudo install -m 0755 -o root -g root -t /usr/local/bin scripts/ip2tor_host.sh
sudo install -m 0755 -o root -g root -t /usr/local/bin scripts/ip2torc.sh
sudo install -m 0755 -o root -g root -t /etc/systemd/system contrib/ip2tor-host.service
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
sudo systemctl enable ip2tor-host
sudo systemctl start ip2tor-host
```

Check the logs using `sudo journalctl --follow -u ip2tor-host`
