# CS2 Translate

Двусторонний перевод голоса в CS2 для **Windows**.

## Быстрый старт (3 шага)

### 1. Установите Python

[python.org/downloads](https://www.python.org/downloads/) — при установке отметьте **Add python.exe to PATH**.

### 2. Установите VB-Audio Virtual Cable

[vb-audio.com/Cable](https://vb-audio.com/Cable/) — перезагрузите ПК.

В Steam один раз: **Settings → Voice → Voice Input Device → CABLE Output (VB-Audio)**.

### 3. Запускайте перед игрой

Двойной клик по **`CS2 Translate.bat`**.

- **Первый запуск** — окно настройки (API-ключ DeepSeek + устройства), нажмите «Сохранить и запустить»
- **Дальше** — просто двойной клик, всё стартует само

Появятся субтитры внизу экрана. **Escape** — выход.

## Что делает программа

```
Команда → вы:   звук игры → субтитры на русском
Вы → команда:  ваш микрофон → английский голос в Steam
```

## Настройки

Повторно открыть настройки:

```powershell
.venv\Scripts\activate
python launcher.py --setup
```

Или удалите `.env` — при следующем запуске откроется мастер настройки.

## CS2

- Режим **оконный** или **borderless** (не exclusive fullscreen)
- Voice chat включён
- **Push-to-talk** в Steam — рекомендуется

## Требования

- Windows 10/11
- Python 3.9+
- VB-Audio Virtual Cable
- API-ключ [DeepSeek](https://platform.deepseek.com/)

## Файлы

| Файл | Назначение |
|------|------------|
| `CS2 Translate.bat` | **Запускайте это перед игрой** |
| `launcher.py` | Мастер настройки + запуск |
| `.env` | Ваши настройки (создаётся автоматически) |

## macOS

<details>
<summary>Инструкция для macOS</summary>

Требуется [BlackHole 2ch](https://existential.audio/blackhole/).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# TEAM_LOOPBACK=false, BlackHole devices
python -m src.main
```

</details>

## Дорожная карта

- [x] EN → RU субтитры
- [x] RU → EN голос в виртуальный микрофон
- [x] Windows WASAPI loopback
- [x] Запуск одним кликом (`CS2 Translate.bat`)
- [ ] Горячие клавиши
- [ ] Игровой словарь CS2
