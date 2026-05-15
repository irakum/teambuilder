class NotFoundError(Exception):
    """Сутність не знайдена в базі даних."""
    pass


class ForbiddenError(Exception):
    """Токен організатора невірний або відсутній."""
    pass


class BusinessRuleError(Exception):
    """Порушення бізнес-правила (наприклад, запуск розподілу без учасників)."""
    pass
