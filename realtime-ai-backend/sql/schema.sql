create table sessions (
  session_id text primary key,
  user_id text,
  start_time timestamptz,
  end_time timestamptz,
  summary text
);

create table session_events (
  id bigint generated always as identity primary key,
  session_id text references sessions(session_id),
  role text,
  content text,
  timestamp timestamptz
);
