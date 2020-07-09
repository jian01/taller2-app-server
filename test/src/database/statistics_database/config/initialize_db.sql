create schema chotuve;

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