CREATE TABLE IF NOT EXISTS monitoring (
  id serial, 
  appname varchar(255) PRIMARY KEY,
  status varchar(7) NOT NULL
);