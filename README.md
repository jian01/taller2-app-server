Master:
[![Build Status](https://travis-ci.com/jian01/taller2-app-server.svg?token=tFcmLjoZ6PFesBqLEXNZ&branch=master)](https://travis-ci.com/jian01/taller2-app-server)
[![Coverage Status](https://coveralls.io/repos/github/jian01/taller2-app-server/badge.svg?branch=master&t=zyUK6K)](https://coveralls.io/github/jian01/taller2-app-server?branch=master)

Develop:
[![Build Status](https://travis-ci.com/jian01/taller2-app-server.svg?token=tFcmLjoZ6PFesBqLEXNZ&branch=develop)](https://travis-ci.com/jian01/taller2-app-server)
[![Coverage Status](https://coveralls.io/repos/github/jian01/taller2-app-server/badge.svg?branch=develop&t=zyUK6K)](https://coveralls.io/github/jian01/taller2-app-server?branch=master)

# Chotuve App Server

La app se crea actualmente en create_application.py, eventualmente necesitara recibir parametros para crearse de alguna config, cuando eso suceda se puede mejorar.

## Logging

Una [convencion de python](https://docs.python.org/3/howto/logging.html) es crear un logger por cada clase diferenciada de la siguiente forma:

```
logger = logging.getLogger(__name__)
```

Vamos a mantener esa convencion para cada clase y loggear con eso.
Python permite configurar para diferenciado por clase y nivel de log tirar 
los logs a archivos rotativos, sumologic, cualquier api, etc.
Podemos extender el logueo en el futuro a gusto, cambiando esta convencion y 
usando las jerarquias de los paquetes para discriminar el trato del log.

Actualmente la configuracion permite loguear solo desde los paquetes en src. (ver *config/logging_conf.ini*)

## Para correr tests

Los unit tests deberan estar en la carpeta test, corren con pytest:

```
pytest test
```

Es importante correr esto desde la raiz del repo ya que es el run path.

Para correr coverage report:

```
pip install -r requirements-travis.txt
pytest --cov=. --cov-report html test/
```

## Para correr la app

Para correr la app con flask:

```
python __main__.py
```

Para correr la app con gunicorn:

```
gunicorn -k sync --workers 3 --bind 0.0.0.0:8080 'create_application:create_application("config/deploy_conf.yml")' --log-config config/logging_conf.ini
```

* `-k` es para indicar el tipo de workers, queremos sync porque andan mejor que el default
* `--workers` es para la cantidad workers simultaneo, como gunicorn es para probar pre-deploy 
y deberia usarse flask para debuggear me parece prudente dejarlo en 3 que seria similar a prod
* `--bind` le indica a que host y puerto mapearlo
* `create_application:create_application` es la ruta a donde importar la app de flask

## Deploy de la app a Heroku

La config del deploy esta en el Procfile.

Actualmente el deploy es manual, luego de instalar heroku cli y estar logueado hay que configurar el remote "heroku" por unica vez:

```
heroku git:remote -a tuapp
```

Despues para deployar:

```
git push heroku master
```

Finalmente para ver los logs:

```
heroku logs
```

## Postgres database

Script para el set-up de la base de datos:

```sql
create schema chotuve;

create table chotuve.users
(
	email varchar,
	fullname varchar,
	phone_number varchar,
	photo varchar,
    admin boolean,
	password varchar
);

create unique index users_email_uindex
	on chotuve.users (email);

alter table chotuve.users
	add constraint users_pk
		primary key (email);

create table chotuve.friend_requests
(
    "from" varchar
        constraint friend_requests_users_email_fk
            references chotuve.users,
    "to" varchar
        constraint friend_requests_users_email_fk_2
            references chotuve.users,
    status varchar,
    timestamp timestamp,
    constraint friend_requests_pk
        primary key ("from", "to")
);

create table chotuve.friends
(
	user1 varchar
		constraint table_name_users_email_fk
			references chotuve.users,
	user2 varchar
		constraint table_name_users_email_fk_2
			references chotuve.users,
	constraint table_name_pk
		unique (user1, user2),
	check (user1 < user2)

create table chotuve.videos
(
	user_email varchar
		constraint videos_users_email_fk
			references chotuve.users,
	title varchar,
	creation_time timestamp,
	visible bool,
	location varchar,
	file_location varchar,
	description varchar,
	constraint videos_pk
		primary key (user_email, title)
);

create table chotuve.video_reactions
(
	reactor_email varchar
		constraint video_reactions_users_email_fk
			references chotuve.users,
	target_email varchar,
	video_title varchar,
	reaction_type int,
	constraint video_reactions_pk
		primary key (reactor_email, target_email, video_title),
	constraint video_reactions_videos_user_email_title_fk
		foreign key (target_email, video_title) references chotuve.videos
);

create table chotuve.user_messages
(
	id serial,
	from_user varchar
		constraint user_messages_users_email_fk
			references chotuve.users,
	to_user varchar
		constraint user_messages_users_email_fk_2
			references chotuve.users,
	message varchar,
    datetime timestamp
);

create unique index user_messages_id_uindex
	on chotuve.user_messages (id);

alter table chotuve.user_messages
	add constraint user_messages_pk
		primary key (id);

create table chotuve.video_comments
(
	author_email varchar
		constraint video_comments_users_email_fk
			references chotuve.users,
	video_owner_email varchar,
	video_title varchar,
	comment varchar,
	datetime timestamp,
	constraint video_comments_pk
		primary key (author_email, video_owner_email, video_title, comment, datetime),
	constraint video_comments_videos_user_email_title_fk
		foreign key (video_owner_email, video_title) references chotuve.videos
);

create table chotuve.app_server_api_calls
(
    id        serial not null,
    alias     varchar,
    path      varchar,
    status    integer,
    datetime  timestamp,
    time      double precision,
    method    varchar
);

create table chotuve.user_notification_tokens
(
	user_email varchar
		constraint user_notification_tokens_pk
			primary key
		constraint user_notification_tokens_users_email_fk
			references chotuve.users
				on delete cascade,
	token varchar
);

create unique index user_notification_tokens_token_uindex
	on chotuve.user_notification_tokens (token);

```