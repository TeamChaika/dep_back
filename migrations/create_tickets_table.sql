-- Создание таблицы tickets (билеты)
CREATE TABLE IF NOT EXISTS tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  promo_code_id UUID REFERENCES promo_codes(id) ON DELETE SET NULL,
  guest_count INTEGER NOT NULL CHECK (guest_count > 0),
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  email TEXT,
  payment_status TEXT NOT NULL DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'cancelled', 'refunded')),
  table_number TEXT,
  comment TEXT,
  guests_checked_in INTEGER NOT NULL DEFAULT 0 CHECK (guests_checked_in >= 0 AND guests_checked_in <= guest_count),
  sms_status TEXT NOT NULL DEFAULT 'pending' CHECK (sms_status IN ('pending', 'sent', 'failed')),
  price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
  discount DECIMAL(10, 2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
  qr_code TEXT UNIQUE NOT NULL, -- Уникальный QR код для проверки
  paid_at TIMESTAMP WITH TIME ZONE,
  checked_in_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  is_deleted BOOLEAN DEFAULT FALSE NOT NULL
);

-- Создание индекса для поиска по событию
CREATE INDEX IF NOT EXISTS idx_tickets_event_id ON tickets(event_id);

-- Создание индекса для поиска по промокоду
CREATE INDEX IF NOT EXISTS idx_tickets_promo_code_id ON tickets(promo_code_id);

-- Создание индекса для поиска по статусу оплаты
CREATE INDEX IF NOT EXISTS idx_tickets_payment_status ON tickets(payment_status);

-- Создание индекса для поиска по QR коду
CREATE INDEX IF NOT EXISTS idx_tickets_qr_code ON tickets(qr_code);

-- Создание индекса для поиска по телефону
CREATE INDEX IF NOT EXISTS idx_tickets_phone ON tickets(phone);

-- Создание индекса для поиска активных билетов
CREATE INDEX IF NOT EXISTS idx_tickets_is_deleted ON tickets(is_deleted) WHERE is_deleted = FALSE;

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_tickets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_tickets_updated_at ON tickets;
CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_tickets_updated_at();

-- Включить RLS (Row Level Security)
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;

-- Удалить существующие политики, если они есть
DROP POLICY IF EXISTS "Users can read tickets for own establishments" ON tickets;
DROP POLICY IF EXISTS "Users can create tickets for own establishments" ON tickets;
DROP POLICY IF EXISTS "Users can update tickets for own establishments" ON tickets;
DROP POLICY IF EXISTS "Public can read tickets by QR code" ON tickets;

-- Политика для чтения билетов (только для своих заведений через события)
CREATE POLICY "Users can read tickets for own establishments" ON tickets
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM events
      INNER JOIN establishments ON establishments.id = events.establishment_id
      WHERE events.id = tickets.event_id
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
      AND events.is_deleted = FALSE
    )
    AND tickets.is_deleted = FALSE
  );

-- Политика для создания билетов (только для своих заведений через события)
CREATE POLICY "Users can create tickets for own establishments" ON tickets
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM events
      INNER JOIN establishments ON establishments.id = events.establishment_id
      WHERE events.id = tickets.event_id
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
      AND events.is_deleted = FALSE
    )
  );

-- Политика для обновления билетов (только для своих заведений через события)
CREATE POLICY "Users can update tickets for own establishments" ON tickets
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM events
      INNER JOIN establishments ON establishments.id = events.establishment_id
      WHERE events.id = tickets.event_id
      AND establishments.owner_id = auth.uid()
      AND establishments.is_deleted = FALSE
      AND events.is_deleted = FALSE
    )
    AND tickets.is_deleted = FALSE
  );

-- Политика для публичного доступа по QR коду (без аутентификации)
-- Это позволит проверять билеты по QR коду
CREATE POLICY "Public can read tickets by QR code" ON tickets
  FOR SELECT USING (
    qr_code IS NOT NULL
    AND is_deleted = FALSE
  );
