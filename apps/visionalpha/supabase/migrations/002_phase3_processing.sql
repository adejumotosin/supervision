create table if not exists public.video_assets (
  id uuid primary key default gen_random_uuid(),
  location_id uuid references public.locations(id) on delete set null,
  storage_provider text not null default 'supabase',
  bucket text not null default 'visionalpha-video',
  object_path text not null,
  original_filename text,
  content_type text,
  size_bytes bigint check (size_bytes is null or size_bytes >= 0),
  duration_seconds numeric(12,3),
  status text not null default 'uploaded'
    check (status in ('uploaded', 'queued', 'processing', 'processed', 'failed')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (bucket, object_path)
);

create table if not exists public.processing_jobs (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references public.video_assets(id) on delete cascade,
  analysis_run_id uuid references public.analysis_runs(id) on delete set null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'succeeded', 'failed', 'canceled')),
  engine text not null default 'yolo_supervision',
  priority smallint not null default 100,
  attempts smallint not null default 0,
  max_attempts smallint not null default 3,
  progress numeric(5,2) not null default 0
    check (progress >= 0 and progress <= 100),
  worker_id text,
  error text,
  metadata jsonb not null default '{}'::jsonb,
  queued_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz
);

alter table public.analysis_runs
  add column if not exists asset_id uuid references public.video_assets(id) on delete set null,
  add column if not exists job_id uuid references public.processing_jobs(id) on delete set null,
  add column if not exists duration_seconds numeric(12,3),
  add column if not exists sample_every integer,
  add column if not exists rates_per_minute jsonb not null default '{}'::jsonb,
  add column if not exists domain_indices jsonb not null default '{}'::jsonb,
  add column if not exists engine_version text;

create index if not exists video_assets_location_created_at_idx
  on public.video_assets (location_id, created_at desc);

create index if not exists processing_jobs_queue_idx
  on public.processing_jobs (status, priority, queued_at);

create index if not exists processing_jobs_asset_idx
  on public.processing_jobs (asset_id, queued_at desc);

create index if not exists analysis_runs_asset_idx
  on public.analysis_runs (asset_id, created_at desc);

alter table public.video_assets enable row level security;
alter table public.processing_jobs enable row level security;

create or replace function public.claim_visionalpha_job(p_worker_id text)
returns setof public.processing_jobs
language plpgsql
security definer
set search_path = public
as $$
begin
  return query
  with next_job as (
    select id
    from public.processing_jobs
    where status = 'queued'
      and attempts < max_attempts
    order by priority asc, queued_at asc
    for update skip locked
    limit 1
  )
  update public.processing_jobs as job
  set status = 'running',
      started_at = now(),
      attempts = job.attempts + 1,
      worker_id = p_worker_id,
      progress = 1
  from next_job
  where job.id = next_job.id
  returning job.*;
end;
$$;

revoke all on function public.claim_visionalpha_job(text) from public;
revoke all on function public.claim_visionalpha_job(text) from anon;
revoke all on function public.claim_visionalpha_job(text) from authenticated;
grant execute on function public.claim_visionalpha_job(text) to service_role;

comment on table public.video_assets is
  'Stored VisionAlpha source footage metadata. Video bytes live in object storage, not Postgres.';
comment on table public.processing_jobs is
  'Queue state for asynchronous semantic video analysis workers.';
