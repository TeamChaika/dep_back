-- Создание таблицы deposits (депозиты/предоплаты)
CREATE TABLE IF NOT EXISTS deposits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  establishment_id UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
  event_id UUID REFERENCES events(id) ON DELETE SET NULL,
  guest_name TEXT NOT NULL,
  guest_phone TEXT NOT NULL,
  guest_email TEXT,
  amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
  visit_date DATE NOT NULL,
  visit_time TIME NOT NULL,
  payment_link TEXT UNIQUE NOT NULL, -- Уникальная ссылка для оплаты
  payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'cancelled', 'refunded')),
  paid_at TIMESTAMP WITH TIME ZONE,
  created_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE, -- Кто создал (хостес/администратор)
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_deleted BOOLEAN DEFAULT FALSE NOT NULL
);

-- Создание индекса для поиска по заведению
CREATE INDEX IF NOT EXISTS idx_deposits_establishment_id ON deposits(establishment_id);

-- Создание индекса для поиска по событию
CREATE INDEX IF NOT EXISTS idx_deposits_event_id ON deposits(event_id);

-- Создание индекса для поиска по статусу оплаты
CREATE INDEX IF NOT EXISTS idx_deposits_payment_status ON deposits(payment_status);

-- Создание индекса для поиска по ссылке оплаты
CREATE INDEX IF NOT EXISTS idx_deposits_payment_link ON deposits(payment_link);

-- Создание индекса для поиска по дате посещения
CREATE INDEX IF NOT EXISTS idx_deposits_visit_date ON deposits(visit_date);

-- Создание индекса для поиска активных депозитов
CREATE INDEX IF NOT EXISTS idx_deposits_is_deleted ON deposits(is_deleted) WHERE is_deleted = FALSE;

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_deposits_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_deposits_updated_at ON deposits;
CREATE TRIGGER update_deposits_updated_at
    BEFORE UPDATE ON deposits
    FOR EACH ROW
    EXECUTE FUNCTION update_deposits_updated_at();

-- Включить RLS (Row Level Security)
ALTER TABLE deposits ENABLE ROW LEVEL SECURITY;

-- Удалить существующие политики, если они есть
DROP POLICY IF EXISTS "Users can read deposits for own establishments" ON deposits;
DROP POLICY IF EXISTS "Users can create deposits for own establishments" ON deposits;
DROP POLICY IF EXISTS "Users can update deposits for own establishments" ON deposits;
DROP POLICY IF EXISTS "Public can read deposits by payment link" ON deposits;

-- Политика для чтения депозитов (только для своих заведений)
CREATE POLICY "Users can read deposits for own establishments" ON deposits
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM establishments 
      WHERE establishments.id = deposits.establishment_id 
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
    )
    AND deposits.is_deleted = FALSE
  );

-- Политика для создания депозитов (только для своих заведений)
CREATE POLICY "Users can create deposits for own establishments" ON deposits
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM establishments 
      WHERE establishments.id = deposits.establishment_id 
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
    )
  );

-- Политика для обновления депозитов (только для своих заведений)
CREATE POLICY "Users can update deposits for own establishments" ON deposits
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM establishments 
      WHERE establishments.id = deposits.establishment_id 
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
    )
    AND deposits.is_deleted = FALSE
  );

-- Политика для публичного доступа по ссылке оплаты (без аутентификации)
-- Это позволит гостю просматривать свой депозит по ссылке
CREATE POLICY "Public can read deposits by payment link" ON deposits
  FOR SELECT USING (
    payment_link IS NOT NULL
    AND is_deleted = FALSE
  );

