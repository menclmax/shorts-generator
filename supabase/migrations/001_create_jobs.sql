create table if not exists jobs (
  id uuid primary key default gen_random_uuid(),
  drive_file_id text not null,
  drive_file_name text,
  status text not null default 'pending',
  error text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(drive_file_id)
);

create index if not exists jobs_status_idx on jobs(status);
create index if not exists jobs_created_idx on jobs(created_at desc);
