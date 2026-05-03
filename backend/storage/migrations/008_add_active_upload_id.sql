-- Migration 008: Add active_upload_id to founders table for persistent sessions
-- Run in: Supabase Dashboard → SQL Editor

ALTER TABLE public.founders 
ADD COLUMN active_upload_id UUID REFERENCES public.uploads(id) ON DELETE SET NULL;

-- Index for performance
CREATE INDEX idx_founders_active_upload_id ON public.founders(active_upload_id);

-- Update RLS policies (founders can already view their own row, which now includes active_upload_id)
