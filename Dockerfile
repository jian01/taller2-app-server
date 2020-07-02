FROM ubuntu:18.04
COPY . /app
WORKDIR /app
RUN apt-get update
RUN apt-get install -qy build-essential wget
RUN apt-get install -qy python3.6 python3.6-dev python3.6-venv python3-distutils
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.6 get-pip.py
RUN apt-get install nginx supervisor -qy
ADD nginx-default /etc/nginx/sites-available/default
RUN echo "\ndaemon off;" >> /etc/nginx/nginx.conf
RUN chown -R www-data:www-data /var/lib/nginx
EXPOSE 80
RUN pip install -r requirements.txt