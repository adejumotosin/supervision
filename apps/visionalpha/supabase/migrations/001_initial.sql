create extension if not exists pgcrypto;

create table if not exists public.locations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  country_code text,
  location_type text not null default 'generic',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  location_id uuid references public.locations(id) on delete set null,
  filename text,
  source_mode text not null,
  frames_total integer not null default 0,
  frames_processed integer not null default 0,
  unique_tracks integer not null default 0,
  activity_index numeric(6,2),
  counts jsonb not null default '{}'::jsonb,
  feature_scores jsonb not null default '{}'::jsonb,
  avg_motion_ratio numeric(12,8),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.activity_baselines (
  id uuid primary key default gen_random_uuid(),
  location_id uuid references public.locations(id) on delete cascade,
  metric_name text not null,
  baseline_value numeric not null,
  valid_from timestamptz not null default now(),
  valid_to timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists analysis_runs_created_at_idx
  on public.analysis_runs (created_at desc);

create index if not exists analysis_runs_location_created_at_idx
  on public.analysis_runs (location_id, created_at desc);

create index if not exists activity_baselines_location_metric_idx
  on public.activity_baselines (location_id, metric_name, valid_from desc);

alter table public.locations enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.activity_baselines enable row level security;

comment on table public.analysis_runs is
  'Timestamped VisionAlpha computer-vision analysis results used to build historical activity indices.';
comment on table public.activity_baselines is
  'Location and metric specific historical baselines for normalizing raw computer-vision observations.';
