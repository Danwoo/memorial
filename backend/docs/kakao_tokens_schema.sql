-- ==========================================
-- Kakao Tokens Table (for OAuth token persistence)
-- ==========================================
-- Run this in Supabase SQL Editor

create table if not exists kakao_tokens (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null unique,
    access_token text not null,
    refresh_token text,
    token_type text default 'bearer',
    expires_in int,
    scope text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Index for fast lookup
create index if not exists kakao_tokens_user_id_idx on kakao_tokens(user_id);

-- Enable RLS
alter table kakao_tokens enable row level security;

-- RLS Policies
create policy "Users can view their own tokens"
on kakao_tokens for select
using (auth.uid() = user_id);

create policy "Users can insert their own tokens"
on kakao_tokens for insert
with check (auth.uid() = user_id);

create policy "Users can update their own tokens"
on kakao_tokens for update
using (auth.uid() = user_id);

create policy "Users can delete their own tokens"
on kakao_tokens for delete
using (auth.uid() = user_id);
