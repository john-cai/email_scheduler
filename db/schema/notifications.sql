drop table if exists notifications;
create table notifications (
    id integer primary key autoincrement,
    reservation_id integer not null,
    end_date date not null,
    first_name text not null,
    last_name text not null,
    email_address text not null
);
