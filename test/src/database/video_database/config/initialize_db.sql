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

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('giancafferata@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false)
ON CONFLICT (email) DO UPDATE
  SET fullname = excluded.fullname,
      phone_number = excluded.phone_number,
      photo = excluded.photo,
      password = excluded.password,
      admin = excluded.admin;