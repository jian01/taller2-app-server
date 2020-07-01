FROM python:3.7
COPY . /app
WORKDIR /app
RUN apt install nginx
COPY ./nginx /etc/nginx/sites-available
RUN pip install -r requirements.txt