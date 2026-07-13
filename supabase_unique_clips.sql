-- Run this once in Supabase SQL Editor before relying on unique clip storage.
-- Existing rating rows are preserved and backfilled into the explicit hierarchy:
-- content_id x prompt x model -> clip_id -> reviewer rating.

create or replace function public.comet_clip_set_key(p_content_id text, p_clip_type text)
returns text
language sql
immutable
as $$
    select p_content_id || '::' ||
        case p_clip_type
            when 'cliffhanger_pro' then 'cliffhanger::pro'
            when 'cliffhanger_flash' then 'cliffhanger::flash'
            when 'momenttype_pro' then 'momenttype::pro'
            when 'momenttype_flash' then 'momenttype::flash'
            else replace(lower(p_clip_type), ' ', '')
        end
$$;

create table if not exists public.clip_sets (
    clip_set_key text primary key,
    content_id text not null,
    content_name text,
    prompt text not null,
    model text not null,
    clip_type text not null,
    output_label text,
    source_status text,
    json_source_file text,
    json_source_link text,
    clip_folder_name text,
    clip_folder_link text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.clips (
    unique_clip_key text primary key,
    clip_set_key text,
    clip_id text not null,
    content_id text not null,
    content_name text,
    prompt text,
    model text,
    clip_type text not null,
    output_label text,
    clip_file_name text,
    clip_drive_link text,
    drive_file_id text,
    genre_cms text,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table if exists public.ratings
    drop constraint if exists ratings_unique_clip_key_fkey,
    drop constraint if exists ratings_clip_set_key_fkey;

alter table if exists public.clips
    drop constraint if exists clips_clip_set_key_fkey;

alter table public.clips
    add column if not exists clip_set_key text,
    add column if not exists prompt text,
    add column if not exists model text;

alter table public.ratings
    add column if not exists clip_set_key text,
    add column if not exists unique_clip_key text,
    add column if not exists feedback_text text,
    add column if not exists rejection_rating integer;

-- Accept/Reject mode stores Accept as 1 and Reject as 0. Older deployments may
-- still have a 1-10 score check, which blocks Reject decisions.
do $$
declare
    constraint_name text;
begin
    for constraint_name in
        select con.conname
        from pg_constraint con
        join pg_class rel on rel.oid = con.conrelid
        join pg_namespace nsp on nsp.oid = rel.relnamespace
        where nsp.nspname = 'public'
          and rel.relname = 'ratings'
          and con.contype = 'c'
          and pg_get_constraintdef(con.oid) ilike '%score%'
    loop
        execute format('alter table public.ratings drop constraint if exists %I', constraint_name);
    end loop;
end $$;

do $$
begin
    if not exists (
        select 1
        from public.ratings
        where score is not null
          and score not in (0, 1)
    ) and not exists (
        select 1
        from pg_constraint
        where conname = 'ratings_score_binary_check'
    ) then
        alter table public.ratings
            add constraint ratings_score_binary_check
            check (score in (0, 1));
    end if;
end $$;

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'ratings_rejection_rating_check'
    ) then
        alter table public.ratings
            add constraint ratings_rejection_rating_check
            check (rejection_rating is null or rejection_rating between 1 and 10);
    end if;
end $$;

update public.ratings
set
    clip_set_key = public.comet_clip_set_key(content_id, clip_type),
    unique_clip_key = public.comet_clip_set_key(content_id, clip_type) || '::' || clip_id
where content_id is not null
  and clip_type is not null
  and clip_id is not null;

insert into public.clip_sets (
    clip_set_key,
    content_id,
    prompt,
    model,
    clip_type
)
select distinct
    clip_set_key,
    content_id,
    split_part(clip_set_key, '::', 2) as prompt,
    split_part(clip_set_key, '::', 3) as model,
    clip_type
from public.ratings
where clip_set_key is not null
on conflict (clip_set_key) do nothing;

insert into public.clips (
    unique_clip_key,
    clip_set_key,
    clip_id,
    content_id,
    prompt,
    model,
    clip_type
)
select distinct
    unique_clip_key,
    clip_set_key,
    clip_id,
    content_id,
    split_part(clip_set_key, '::', 2) as prompt,
    split_part(clip_set_key, '::', 3) as model,
    clip_type
from public.ratings
where unique_clip_key is not null
on conflict (unique_clip_key) do nothing;

drop index if exists public.ratings_unique_clip_reviewer_idx;

create unique index ratings_unique_clip_reviewer_idx
    on public.ratings (unique_clip_key, reviewer_email);

create unique index if not exists ratings_legacy_clip_reviewer_idx
    on public.ratings (clip_id, content_id, clip_type, reviewer_email);

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'clips_clip_set_key_fkey'
    ) then
        alter table public.clips
            add constraint clips_clip_set_key_fkey
            foreign key (clip_set_key)
            references public.clip_sets(clip_set_key)
            on update cascade
            on delete restrict;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'ratings_clip_set_key_fkey'
    ) then
        alter table public.ratings
            add constraint ratings_clip_set_key_fkey
            foreign key (clip_set_key)
            references public.clip_sets(clip_set_key)
            on update cascade
            on delete restrict;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'ratings_unique_clip_key_fkey'
    ) then
        alter table public.ratings
            add constraint ratings_unique_clip_key_fkey
            foreign key (unique_clip_key)
            references public.clips(unique_clip_key)
            on update cascade
            on delete restrict;
    end if;
end $$;

-- The Streamlit app currently connects with the Supabase anon key, not a
-- Supabase-authenticated user. Keep RLS disabled unless matching policies are
-- added later.
alter table public.clip_sets disable row level security;
alter table public.clips disable row level security;
alter table public.ratings disable row level security;
