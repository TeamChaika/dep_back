-- Миграция для добавления колонки is_deleted в таблицу establishments
-- Позволяет администраторам помечать заведения как удаленные без физического удаления

-- Добавить колонку is_deleted
ALTER TABLE establishments 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;

-- Создать индекс для быстрого поиска активных заведений
CREATE INDEX IF NOT EXISTS idx_establishments_is_deleted ON establishments(is_deleted) WHERE is_deleted = FALSE;

-- Обновить существующие записи, чтобы они не были помечены как удаленные
UPDATE establishments SET is_deleted = FALSE WHERE is_deleted IS NULL;

