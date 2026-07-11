-- First, drop existing tables if they exist
DROP TABLE IF EXISTS public.properties CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- Create users table
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    location JSONB NOT NULL,
    user_type TEXT NOT NULL CHECK (user_type IN ('user', 'provider')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create properties table
CREATE TABLE public.properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    price NUMERIC NOT NULL,
    bedrooms TEXT NOT NULL,
    bathrooms TEXT NOT NULL,
    area NUMERIC NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    image_url TEXT DEFAULT 'https://via.placeholder.com/300x200?text=Property+Image',
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'rented')),
    provider_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    latitude TEXT DEFAULT '27.7172',
    longitude TEXT DEFAULT '85.3240',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Add Row Level Security (RLS) policies

-- Enable RLS on tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY;

-- Allow public inserts to users table (for registration)
CREATE POLICY "Allow public inserts" 
ON public.users
FOR INSERT 
TO public
WITH CHECK (true);

-- Allow users to view their own data
CREATE POLICY "Users can view own data" 
ON public.users
FOR SELECT 
TO authenticated
USING (auth.uid() = id);

-- Allow users to update their own data
CREATE POLICY "Users can update own data" 
ON public.users
FOR UPDATE 
TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- Properties policies

-- Allow anyone to view available properties
CREATE POLICY "Anyone can view available properties" 
ON public.properties
FOR SELECT 
TO public
USING (status = 'available');

-- Allow providers to insert their own properties
CREATE POLICY "Providers can insert properties" 
ON public.properties
FOR INSERT 
TO authenticated
WITH CHECK (provider_id = auth.uid());

-- Allow providers to update their own properties
CREATE POLICY "Providers can update own properties" 
ON public.properties
FOR UPDATE 
TO authenticated
USING (provider_id = auth.uid())
WITH CHECK (provider_id = auth.uid());

-- Allow providers to delete their own properties
CREATE POLICY "Providers can delete own properties" 
ON public.properties
FOR DELETE 
TO authenticated
USING (provider_id = auth.uid());

-- Create indexes for better performance
CREATE INDEX idx_users_phone ON public.users(phone);
CREATE INDEX idx_users_user_type ON public.users(user_type);
CREATE INDEX idx_properties_provider_id ON public.properties(provider_id);
CREATE INDEX idx_properties_status ON public.properties(status);

-- Grant permissions to authenticated and anon roles
GRANT ALL ON public.users TO authenticated;
GRANT ALL ON public.properties TO authenticated;
GRANT SELECT ON public.properties TO anon;
GRANT INSERT ON public.users TO anon; 