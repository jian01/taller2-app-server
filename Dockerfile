FROM ubuntu:18.04
COPY . /app
WORKDIR /app
RUN apt-get update
RUN apt-get install -qy python \
                        python-dev \
                        python-pip \
                        python-setuptools \
                        build-essential
RUN apt-get install nginx supervisor -qy
ADD nginx-default /etc/nginx/sites-available/default
RUN echo "\ndaemon off;" >> /etc/nginx/nginx.conf
RUN chown -R www-data:www-data /var/lib/nginx
EXPOSE 80
RUN pip install -r requirements.txt