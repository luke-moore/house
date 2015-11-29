deploy:
	sudo $(MAKE) deploy_as_root

deploy_as_root:
	/etc/init.d/apache2 stop
	rm -rf /var/www/django
	cp -r django /var/www/
	cd /var/www/django && ./manage.py migrate
	cd /var/www/django && ./manage.py collectstatic --noinput
	chmod -R a+r /var/www/django
	/etc/init.d/apache2 start
