FROM ubuntu:18.04
COPY . /app
WORKDIR /app
RUN apt-get update
RUN apt-get install -qy build-essential wget gettext-base
RUN apt-get install -qy python3.6 python3.6-dev python3.6-venv python3-distutils
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3.6 get-pip.py
RUN apt-get install nginx supervisor -qy
COPY default.conf.template /etc/nginx/conf.d/default.conf.template
RUN echo "\ndaemon off;" >> /etc/nginx/nginx.conf
RUN pip install -r requirements.txt
RUN python3.6 -c "import nltk; nltk.download('punkt', download_dir='/usr/nltk_data')"