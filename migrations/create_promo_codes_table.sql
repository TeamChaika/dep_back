-- Создание таблицы promo_codes (промокоды)
CREATE TABLE IF NOT EXISTS promo_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  promo_type TEXT NOT NULL CHECK (promo_type IN ('fixed', 'percentage')),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  discount_value DECIMAL(10, 2) NOT NULL CHECK (discount_value > 0),
  start_date TIMESTAMP WITH TIME ZONE NOT NULL,
  end_date TIMESTAMP WITH TIME ZONE NOT NULL,
  max_uses INTEGER, -- Максимальное количество использований (NULL = без ограничений)
  current_uses INTEGER NOT NULL DEFAULT 0 CHECK (current_uses >= 0),
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
  CONSTRAINT check_dates CHECK (end_date > start_date),
  CONSTRAINT check_fixed_discount CHECK (
    (promo_type = 'fixed' AND discount_value > 0) OR
    (promo_type = 'percentage' AND discount_value > 0 AND discount_value <= 100)
  )
);

-- Создание индекса для поиска по коду промокода
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);

-- Создание индекса для поиска по событию
CREATE INDEX IF NOT EXISTS idx_promo_codes_event_id ON promo_codes(event_id);

-- Создание индекса для поиска активных промокодов
CREATE INDEX IF NOT EXISTS idx_promo_codes_is_active ON promo_codes(is_active) WHERE is_active = TRUE AND is_deleted = FALSE;

-- Создание индекса для поиска по датам действия
CREATE INDEX IF NOT EXISTS idx_promo_codes_dates ON promo_codes(start_date, end_date);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_promo_codes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_promo_codes_updated_at ON promo_codes;
CREATE TRIGGER update_promo_codes_updated_at
    BEFORE UPDATE ON promo_codes
    FOR EACH ROW
    EXECUTE FUNCTION update_promo_codes_updated_at();

-- Включить RLS (Row Level Security)
ALTER TABLE promo_codes ENABLE ROW LEVEL SECURITY;

-- Удалить существующие политики, если они есть
DROP POLICY IF EXISTS "Users can read promo codes for own establishments" ON promo_codes;
DROP POLICY IF EXISTS "Users can create promo codes for own establishments" ON promo_codes;
DROP POLICY IF EXISTS "Users can update promo codes for own establishments" ON promo_codes;
DROP POLICY IF EXISTS "Public can read active promo codes" ON promo_codes;

-- Политика для чтения промокодов (только для своих заведений через события)
CREATE POLICY "Users can read promo codes for own establishments" ON promo_codes
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM events
      INNER JOIN establishments ON establishments.id = events.establishment_id
      WHERE events.id = promo_codes.event_id
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
      AND events.is_deleted = FALSE
    )
    AND promo_codes.is_deleted = FALSE
  );

-- Политика для создания промокодов (только для своих заведений через события)
CREATE POLICY "Users can create promo codes for own establishments" ON promo_codes
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM events
      INNER JOIN establishments ON establishments.id = events.establishment_id
      WHERE events.id = promo_codes.event_id
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
      AND events.is_deleted = FALSE
    )
  );

-- Политика для обновления промокодов (только для своих заведений через события)
CREATE POLICY "Users can update promo codes for own establishments" ON promo_codes
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM events
      INNER JOIN establishments ON establishments.id = events.establishment_id
      WHERE events.id = promo_codes.event_id
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
      AND events.is_deleted = FALSE
    )
    AND promo_codes.is_deleted = FALSE
  );

-- Политика для публичного доступа к активным промокодам (для проверки при покупке билетов)
CREATE POLICY "Public can read active promo codes" ON promo_codes
  FOR SELECT USING (
    is_active = TRUE
    AND is_deleted = FALSE
    AND NOW() >= start_date
    AND NOW() <= end_date
    AND (max_uses IS NULL OR current_uses < max_uses)
  );
