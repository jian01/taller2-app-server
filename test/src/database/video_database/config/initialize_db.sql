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

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('giancafferata@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('cafferatagian@hotmail.com', 'Gianmarco', '1111', 'asd', 'asd123', false);

INSERT INTO chotuve.users (email, fullname, phone_number, photo, password, admin)
VALUES ('asd@asd.com', 'Gianmarco', '1111', 'asd', 'asd123', false);