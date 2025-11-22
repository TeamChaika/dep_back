-- Создание таблицы establishments (заведения)
CREATE TABLE IF NOT EXISTS establishments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  address TEXT NOT NULL,
  working_hours JSONB NOT NULL,
  social_networks JSONB,
  description TEXT,
  owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создание индекса для поиска по названию
CREATE INDEX IF NOT EXISTS idx_establishments_name ON establishments(name);

-- Создание индекса для поиска по адресу
CREATE INDEX IF NOT EXISTS idx_establishments_address ON establishments(address);

-- Создание индекса для поиска по владельцу
CREATE INDEX IF NOT EXISTS idx_establishments_owner_id ON establishments(owner_id);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_establishments_updated_at ON establishments;
CREATE TRIGGER update_establishments_updated_at
    BEFORE UPDATE ON establishments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Включить RLS (Row Level Security)
ALTER TABLE establishments ENABLE ROW LEVEL SECURITY;

-- Удалить существующие политики, если они есть
DROP POLICY IF EXISTS "Users can read own establishments" ON establishments;
DROP POLICY IF EXISTS "Users can create own establishments" ON establishments;
DROP POLICY IF EXISTS "Users can update own establishments" ON establishments;
DROP POLICY IF EXISTS "Users can delete own establishments" ON establishments;
DROP POLICY IF EXISTS "Anyone can read establishments" ON establishments;
DROP POLICY IF EXISTS "Authenticated users can create establishments" ON establishments;
DROP POLICY IF EXISTS "Authenticated users can update establishments" ON establishments;
DROP POLICY IF EXISTS "Authenticated users can delete establishments" ON establishments;

-- Политика для чтения заведений (только свои заведения)
CREATE POLICY "Users can read own establishments" ON establishments
  FOR SELECT USING (auth.uid() = owner_id);

-- Политика для создания заведений (только авторизованные пользователи, owner_id = текущий пользователь)
CREATE POLICY "Users can create own establishments" ON establishments
  FOR INSERT WITH CHECK (auth.uid() = owner_id);

-- Политика для обновления заведений (только владелец)
CREATE POLICY "Users can update own establishments" ON establishments
  FOR UPDATE USING (auth.uid() = owner_id);

-- Политика для удаления заведений (только владелец)
CREATE POLICY "Users can delete own establishments" ON establishments
  FOR DELETE USING (auth.uid() = owner_id);

