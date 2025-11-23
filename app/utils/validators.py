import re

def validate_phone_number(v: str | None) -> str | None:
    """
    Валидация телефона по маске +7###-###-##-##.
    Принимает строку, удаляет лишние символы, проверяет формат и возвращает отформатированную строку.
    """
    if v is None:
        return None
        
    # Удаляем все пробелы и дефисы для проверки
    cleaned = re.sub(r"[\s-]", "", v)
    
    # Проверяем формат +7XXXXXXXXXX (11 цифр после +7)
    pattern = r"^\+7\d{10}$"
    if not re.match(pattern, cleaned):
        raise ValueError(
            "Телефон должен быть в формате +7###-###-##-## (например: +7999-123-45-67)"
        )
        
    # Возвращаем в формате с дефисами, если их нет или формат неправильный
    # Форматируем: +7XXX-XXX-XX-XX
    formatted = f"+7{cleaned[2:5]}-{cleaned[5:8]}-{cleaned[8:10]}-{cleaned[10:12]}"
    return formatted

