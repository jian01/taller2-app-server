FROM nginx:1.18.0
COPY . /app
COPY nginx.conf /etc/nginx/nginx.conf
WORKDIR /app
RUN pip install -r requirements.txt