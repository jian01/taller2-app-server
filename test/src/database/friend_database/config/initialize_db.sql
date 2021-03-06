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
);

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

create table chotuve.deleted_messages
(
	id int
		constraint deleted_messages_user_messages_id_fk
			references chotuve.user_messages (id),
	deletor varchar
		constraint deleted_messages_users_email_fk
			references chotuve.users,
	constraint deleted_messages_pk
		primary key (id, deletor)
);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('giancafferata@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('cafferatagian@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('asd@asd.com', 'Gianmarco', '1111', 'asd', 'asd123', false);