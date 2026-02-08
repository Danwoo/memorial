-- Enable pgvector extension for embedding search
create extension if not exists vector;

-- ==========================================
-- 1. Memories Table (Knowledge Base)
-- ==========================================
create table if not exists memories (
    id uuid primary key default gen_random_uuid(),
    user_id uuid default auth.uid(), -- Link to Supabase Auth User
    source_type text not null check (source_type in ('WEB', 'PDF', 'NOTE')),
    title text not null,
    content text not null,
    summary text,
    tags text[], -- Array of strings
    status text default 'processing' check (status in ('processing', 'completed', 'discarded')),
    
    -- Metadata for source tracing (url, file_path, etc.)
    metadata jsonb default '{}'::jsonb,
    
    -- Vector Embedding (OpenAI text-embedding-3-small: 1536 dims)
    embedding vector(1536),
    
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- Indexes for performance
create index if not exists memories_user_id_idx on memories(user_id);
create index if not exists memories_status_idx on memories(status);

-- Vector Search Index (HNSW for speed)
-- Note: Create this AFTER inserting some data for better indexing, or usually safe to create early
create index if not exists memories_embedding_idx on memories 
using hnsw (embedding vector_cosine_ops);


-- ==========================================
-- 2. Chat Sessions (Conversation History)
-- ==========================================
create table if not exists chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid default auth.uid(),
    title text default 'New Chat',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists chat_sessions_user_id_idx on chat_sessions(user_id);


-- ==========================================
-- 3. Chat Messages
-- ==========================================
create table if not exists chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references chat_sessions(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    token_count int,
    created_at timestamptz default now()
);

create index if not exists chat_messages_session_id_idx on chat_messages(session_id);


-- ==========================================
-- 4. Row Level Security (RLS) Policies
-- Secure data so users can only access their own rows
-- ==========================================

-- Enable RLS
alter table memories enable row level security;
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;

-- Memories Policies
create policy "Users can view their own memories"
on memories for select
using (auth.uid() = user_id);

create policy "Users can insert their own memories"
on memories for insert
with check (auth.uid() = user_id);

create policy "Users can update their own memories"
on memories for update
using (auth.uid() = user_id);

create policy "Users can delete their own memories"
on memories for delete
using (auth.uid() = user_id);

-- Chat Sessions Policies
create policy "Users can view their own sessions"
on chat_sessions for select
using (auth.uid() = user_id);

create policy "Users can insert their own sessions"
on chat_sessions for insert
with check (auth.uid() = user_id);

-- Chat Messages Policies
-- Indirectly checked via session access, but good to be explicit or join
create policy "Users can view messages of their sessions"
on chat_messages for select
using (
    exists (
        select 1 from chat_sessions
        where chat_sessions.id = chat_messages.session_id
        and chat_sessions.user_id = auth.uid()
    )
);

create policy "Users can insert messages to their sessions"
on chat_messages for insert
with check (
    exists (
        select 1 from chat_sessions
        where chat_sessions.id = chat_messages.session_id
        and chat_sessions.user_id = auth.uid()
    )
);
