# Конфигурация правил снятия групп в игре Го

# Возможные значения capture_mode:
#   - "white_only": снимаются только белые окружённые группы
#   - "black_only": снимаются только чёрные окружённые группы
#   - "both": снимаются все окружённые группы
capture_mode = "both"

# delayed_capture:
#   - True: окружённые группы игрока удаляются в начале следующего хода (отложено)
#   - False: окружённые группы удаляются сразу после хода
delayed_capture = True
