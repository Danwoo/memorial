-- Create journals table
CREATE TABLE IF NOT EXISTS public.journals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    content TEXT NOT NULL,
    mood VARCHAR(50),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.journals ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view their own journals" 
ON public.journals FOR SELECT 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own journals" 
ON public.journals FOR INSERT 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own journals" 
ON public.journals FOR UPDATE 
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own journals" 
ON public.journals FOR DELETE 
USING (auth.uid() = user_id);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_journals_user_id ON public.journals(user_id);
CREATE INDEX IF NOT EXISTS idx_journals_created_at ON public.journals(created_at);
