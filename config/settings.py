
# --- Общие параметры игры Go ---

# Размер доски (по умолчанию 9x9)
BOARD_SIZE = 9

# Режим удаления групп:
# 'both' — снимать все окружённые группы
# 'white_only' — снимать только белые
# 'black_only' — снимать только чёрные
CAPTURE_MODE = "both"

# True — задержанное удаление групп игрока
# False — немедленное удаление
DELAYED_CAPTURE = True

# Очередь ходов:
#   'deterministic' — по шаблону (например, 'ЧБЧЧБ')
#   'random' — случайная очередь, с предсказуемым seed
QUEUE_MODE = "deterministic"
QUEUE_PATTERN = "ЧБ"       # Только если deterministic
QUEUE_SEED = 42            # Только если random
QUEUE_CHUNK_SIZE = 200

# Задержка между ходами (сек.)
STEP_DELAY = 0.3
