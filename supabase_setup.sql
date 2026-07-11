-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    location JSONB,
    user_type TEXT NOT NULL CHECK (user_type IN ('user', 'provider')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create properties table
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    price NUMERIC NOT NULL,
    bedrooms TEXT NOT NULL,
    bathrooms TEXT NOT NULL,
    area NUMERIC NOT NULL,
    location TEXT NOT NULL,
    description TEXT,
    image_url TEXT,
    status TEXT NOT NULL CHECK (status IN ('available', 'rented')),
    provider_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_properties_provider_id ON properties(provider_id);
CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);

-- Create Row Level Security (RLS) policies
-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if needed
DROP POLICY IF EXISTS "Users can view their own data" ON users;
DROP POLICY IF EXISTS "Users can update their own data" ON users;
DROP POLICY IF EXISTS "Allow user registration" ON users;
DROP POLICY IF EXISTS "Anyone can view available properties" ON properties;
DROP POLICY IF EXISTS "Providers can view their own properties" ON properties;
DROP POLICY IF EXISTS "Providers can insert their own properties" ON properties;
DROP POLICY IF EXISTS "Providers can update their own properties" ON properties;
DROP POLICY IF EXISTS "Providers can delete their own properties" ON properties;

-- Create policies for users table
CREATE POLICY "Users can view their own data" 
    ON users FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own data" 
    ON users FOR UPDATE 
    USING (auth.uid() = id);

-- Allow inserting new users during registration
CREATE POLICY "Allow user registration" 
    ON users FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

-- Create policies for properties table
CREATE POLICY "Anyone can view available properties" 
    ON properties FOR SELECT 
    USING (status = 'available');

CREATE POLICY "Providers can view their own properties" 
    ON properties FOR SELECT 
    USING (provider_id = auth.uid());

CREATE POLICY "Providers can insert their own properties" 
    ON properties FOR INSERT 
    WITH CHECK (provider_id = auth.uid());

CREATE POLICY "Providers can update their own properties" 
    ON properties FOR UPDATE 
    USING (provider_id = auth.uid());

CREATE POLICY "Providers can delete their own properties" 
    ON properties FOR DELETE 
    USING (provider_id = auth.uid()); 