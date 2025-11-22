-- Миграция для добавления колонки is_deleted в таблицу users
-- Позволяет администраторам помечать аккаунты как удаленные без физического удаления

-- Добавить колонку is_deleted
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;

-- Создать индекс для быстрого поиска активных пользователей
CREATE INDEX IF NOT EXISTS idx_users_is_deleted ON users(is_deleted) WHERE is_deleted = FALSE;

-- Обновить существующие записи, чтобы они не были помечены как удаленные
UPDATE users SET is_deleted = FALSE WHERE is_deleted IS NULL;

