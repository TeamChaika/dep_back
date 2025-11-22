-- Создание таблицы events (события)
CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  establishment_id UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  event_date DATE NOT NULL,
  event_time TIME NOT NULL,
  poster_url TEXT,
  ticket_types JSONB NOT NULL DEFAULT '[]'::jsonb,
  start_sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
  end_sale_date TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_deleted BOOLEAN DEFAULT FALSE NOT NULL
);

-- Создание индекса для поиска по заведению
CREATE INDEX IF NOT EXISTS idx_events_establishment_id ON events(establishment_id);

-- Создание индекса для поиска по дате события
CREATE INDEX IF NOT EXISTS idx_events_event_date ON events(event_date);

-- Создание индекса для поиска активных событий
CREATE INDEX IF NOT EXISTS idx_events_is_deleted ON events(is_deleted) WHERE is_deleted = FALSE;

-- Создание индекса для поиска по дате начала продаж
CREATE INDEX IF NOT EXISTS idx_events_start_sale_date ON events(start_sale_date);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_events_updated_at ON events;
CREATE TRIGGER update_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE FUNCTION update_events_updated_at();

-- Включить RLS (Row Level Security)
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Удалить существующие политики, если они есть
DROP POLICY IF EXISTS "Users can read own establishment events" ON events;
DROP POLICY IF EXISTS "Users can create events for own establishments" ON events;
DROP POLICY IF EXISTS "Users can update own establishment events" ON events;
DROP POLICY IF EXISTS "Users can delete own establishment events" ON events;

-- Политика для чтения событий (только события своих заведений)
CREATE POLICY "Users can read own establishment events" ON events
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM establishments 
      WHERE establishments.id = events.establishment_id 
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
    )
    AND events.is_deleted = FALSE
  );

-- Политика для создания событий (только для своих заведений)
CREATE POLICY "Users can create events for own establishments" ON events
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM establishments 
      WHERE establishments.id = events.establishment_id 
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
    )
  );

-- Политика для обновления событий (только события своих заведений)
CREATE POLICY "Users can update own establishment events" ON events
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM establishments 
      WHERE establishments.id = events.establishment_id 
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
    )
    AND events.is_deleted = FALSE
  );

-- Политика для удаления событий (только администраторы, через is_deleted)
-- Обычные пользователи не могут удалять, только администраторы через API

