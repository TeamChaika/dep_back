-- Миграция для добавления колонки is_admin в таблицу users
-- Позволяет определять администраторов сервиса

-- Добавить колонку is_admin
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- Создать индекс для быстрого поиска администраторов
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin) WHERE is_admin = TRUE;

-- Обновить существующие записи, чтобы они не были администраторами по умолчанию
UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL;

