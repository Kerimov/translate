# CS2 Translate

Двусторонний перевод голоса в CS2:
- **Команда → вы:** английская речь → русские субтитры на экране
- **Вы → команда:** русская речь → английский голос в виртуальный микрофон

## Как это работает

```
Входящий:  Звук игры → Whisper (EN) → DeepSeek → субтитры RU
Исходящий: Ваш микрофон → Whisper (RU) → DeepSeek → Edge TTS (EN) → VB-Cable → Steam
```

## Требования

- **Windows 10/11** (основная платформа для CS2)
- Python 3.9+
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) (бесплатный виртуальный аудиокабель)
- API-ключ [DeepSeek](https://platform.deepseek.com/)

> macOS тоже поддерживается — см. раздел [macOS](#macos) внизу.

## Установка (Windows)

```powershell
cd translate
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Вставьте DEEPSEEK_API_KEY в .env
```

Или просто двойной клик по `run.bat` (создаст venv и запустит).

## Настройка аудио для CS2 (Windows)

### 1. Установите VB-Audio Virtual Cable

Скачайте с [vb-audio.com/Cable](https://vb-audio.com/Cable/) и перезагрузите ПК.

Появятся два устройства:
- **CABLE Input** — куда приложение отправляет переведённый английский голос
- **CABLE Output** — что Steam использует как микрофон

### 2. Захват голоса команды (WASAPI loopback)

На Windows **не нужен** отдельный аудиокабель для входящего звука — приложение захватывает звук игры напрямую через **WASAPI loopback** (по умолчанию `TEAM_LOOPBACK=true`).

Вы продолжаете слышать игру в наушниках как обычно.

### 3. Найдите индексы устройств

```powershell
.venv\Scripts\activate
python -m src.main --list-devices
```

Пример `.env`:

```env
TEAM_LOOPBACK=true
# TEAM_AUDIO_DEVICE=4    # наушники (если не default output)
MIC_INPUT_DEVICE=1       # ваш микрофон
VIRTUAL_MIC_DEVICE=5     # CABLE Input (VB-Audio)
```

### 4. Steam / CS2

1. **Steam → Settings → Voice → Voice Input Device → CABLE Output (VB-Audio Virtual Cable)**
2. Voice chat включён в CS2
3. **Push-to-talk** в Steam — меньше лишнего перевода
4. CS2 в **оконном** или **borderless** режиме — оверлей поверх игры

## Запуск (Windows)

```powershell
.venv\Scripts\activate
python -m src.main
```

Или `run.bat`.

- Субтитры команды — белым, ваш перевод — голубым
- **Escape** на оверлее — выход
- Первый запуск скачает модели Whisper (~150 MB + ~460 MB)

## Настройки (.env)

| Переменная | Описание |
|------------|----------|
| `DEEPSEEK_API_KEY` | Ключ API DeepSeek |
| `TEAM_LOOPBACK` | Захват звука игры через WASAPI (`true` на Windows по умолчанию) |
| `TEAM_AUDIO_DEVICE` | Индекс устройства **вывода** для loopback (наушники) |
| `MIC_INPUT_DEVICE` | Ваш микрофон |
| `VIRTUAL_MIC_DEVICE` | **CABLE Input** — виртуальный мик для Steam |
| `WHISPER_MODEL_IN` | Модель для EN (`small.en`) |
| `WHISPER_MODEL_OUT` | Модель для RU (`small`) |
| `TTS_VOICE` | Голос Edge TTS |
| `ENABLE_OUTGOING` | RU→EN голос (`true`/`false`) |
| `SHOW_ORIGINAL` | Показывать английский над субтитрами |

## Советы для CS2

- Говорите **коротко**: «Раш B», «Флеш», «Один на A»
- `small.en` + `small` — баланс скорости и качества
- Задержка исходящего ~2–4 сек — используйте push-to-talk
- Если команда не слышит — проверьте `VIRTUAL_MIC_DEVICE` и микрофон в Steam (CABLE Output)
- Приложение **не внедряется в игру** — VAC-safe

## macOS

<details>
<summary>Инструкция для macOS</summary>

### Требования

- [BlackHole 2ch](https://existential.audio/blackhole/)

### Настройка

1. Создайте **Multi-Output Device** (BlackHole + наушники) в Audio MIDI Setup
2. В `.env`:
   ```env
   TEAM_LOOPBACK=false
   TEAM_AUDIO_DEVICE=2    # BlackHole input
   VIRTUAL_MIC_DEVICE=3   # BlackHole output
   ```
3. Steam → Voice Input → BlackHole 2ch

### Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

</details>

## Дорожная карта

- [x] EN → RU субтитры (оверлей)
- [x] RU → EN голос в виртуальный микрофон
- [x] Windows WASAPI loopback
- [ ] Горячие клавиши, настройка позиции оверлея
- [ ] Игровой словарь CS2
