-- Migration 007: Chat history table for Ask AI persistence
-- Run in: Supabase Dashboard → SQL Editor

CREATE TABLE IF NOT EXISTS public.chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    founder_id UUID NOT NULL REFERENCES public.founders(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'error')),
    content TEXT NOT NULL,
    agent_details JSONB DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Optional: Link to a specific upload if the query was about one file
    upload_id UUID REFERENCES public.uploads(id) ON DELETE SET NULL
);

-- Enable RLS
ALTER TABLE public.chat_history ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Founders can view their own chat history"
    ON public.chat_history FOR SELECT
    USING (auth.uid() = founder_id);

CREATE POLICY "Founders can insert their own chat history"
    ON public.chat_history FOR INSERT
    WITH CHECK (auth.uid() = founder_id);

-- Indexes for performance
CREATE INDEX idx_chat_history_founder_id ON public.chat_history(founder_id);
CREATE INDEX idx_chat_history_created_at ON public.chat_history(created_at DESC);
