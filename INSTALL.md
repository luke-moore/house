Installation:
-------------
- Edit /etc/hostname and set the machine name to house.
- aptsudo -get install apache2 libapache2-mod-wsgi mysql-server python-mysqldb openssh-server python-dev rabbitmq-server
- The ouimeaux Python module needs to write configuration data to the home
  directory, so create a home directory for the www-data user:
mkdir /home/www-data && chown www-data:www-data /home/www-data && /etc/init.d/apache2 stop && usermod -d /home/www-data www-data && /etc/init.d/apache2 start
- sudo pip install django==1.8
- sudo pip install psutil
- sudo pip install celery
- sudo pip install django-celery
- sudo pip install oiumeaux
- cp installation_files/etc/default/celeryd /etc/default/
- cp installation_files/etc/init.d/celeryd /etc/init.d/
- sudo update-rc.d celeryd defaults
- Create /etc/modprobe.d/blacklist-iguanair.conf to contain
blacklist iguanair
- Install the iguanaIR .deb packages (http://www.iguanaworks.net/files/?OS=DEB)
- Edit /etc/udev/rules.d/70-persistent-net.rules and add
ATTRS{idVendor}=="1781",ATTRS{idProduct}=="0938",MODE="0666",GROUP="iguanair"
  or
  Change /etc/init.d/iguanaIR so it runs as root
- Create the house database, grant the www mysql user access to it.
- Edit /etc/apache2/sites-available/000-default.conf and add
  At the top:
    WSGIPythonPath /var/www/django
  In the VirtualHost section:
        ServerName house.local
	WSGIScriptAlias / /var/www/django/housesite/wsgi.py
	<Directory /var/www/django/housesite>
	<Files wsgi.py>
	Require all granted
	</Files>
	</Directory>

	Alias /static /var/www/django/housesite/static
- sudo make deploy

Configuration:
--------------
- housesite/settings.py
    - Set your database password (search for DATABASES).
    - Set HUELIGHTS_USERNAME to set your username for Philips Hue.
- sudo make deploy

-------
Convience settings:
- visudo and add
Defaults timestamp_timeout=30
