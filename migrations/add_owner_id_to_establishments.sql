-- Миграция для добавления owner_id в существующую таблицу establishments
-- Выполните этот скрипт, если таблица establishments уже создана без поля owner_id

-- Добавить колонку owner_id
ALTER TABLE establishments 
ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Установить NOT NULL после заполнения данных (если нужно)
-- ALTER TABLE establishments ALTER COLUMN owner_id SET NOT NULL;

-- Создать индекс для поиска по владельцу
CREATE INDEX IF NOT EXISTS idx_establishments_owner_id ON establishments(owner_id);

-- Удалить старые политики RLS
DROP POLICY IF EXISTS "Anyone can read establishments" ON establishments;
DROP POLICY IF EXISTS "Authenticated users can create establishments" ON establishments;
DROP POLICY IF EXISTS "Authenticated users can update establishments" ON establishments;
DROP POLICY IF EXISTS "Authenticated users can delete establishments" ON establishments;

-- Создать новые политики RLS с проверкой владельца
CREATE POLICY "Users can read own establishments" ON establishments
  FOR SELECT USING (auth.uid() = owner_id);

CREATE POLICY "Users can create own establishments" ON establishments
  FOR INSERT WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Users can update own establishments" ON establishments
  FOR UPDATE USING (auth.uid() = owner_id);

CREATE POLICY "Users can delete own establishments" ON establishments
  FOR DELETE USING (auth.uid() = owner_id);

