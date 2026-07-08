-- Run this once in Supabase SQL Editor before relying on unique clip storage.
-- Existing rating rows are preserved.

create table if not exists public.clips (
    unique_clip_key text primary key,
    clip_id text not null,
    content_id text not null,
    content_name text,
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

alter table public.ratings
    add column if not exists unique_clip_key text;

update public.ratings
set unique_clip_key = content_id || '::' || clip_type || '::' || clip_id
where unique_clip_key is null
  and content_id is not null
  and clip_type is not null
  and clip_id is not null;

insert into public.clips (
    unique_clip_key,
    clip_id,
    content_id,
    clip_type
)
select distinct
    unique_clip_key,
    clip_id,
    content_id,
    clip_type
from public.ratings
where unique_clip_key is not null
on conflict (unique_clip_key) do nothing;

create unique index if not exists ratings_unique_clip_reviewer_idx
    on public.ratings (unique_clip_key, reviewer_email);

do $$
begin
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
