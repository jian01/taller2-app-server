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

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('giancafferata@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('cafferatagian@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('asd@asd.com', 'Gianmarco', '1111', 'asd', 'asd123', false);