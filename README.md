# CS2 Translate

Двусторонний перевод голоса в CS2:
- **Команда → вы:** английская речь → русские субтитры на экране
- **Вы → команда:** русская речь → английский голос в виртуальный микрофон

## Как это работает

```
Входящий:  Голос из игры → Whisper (EN) → DeepSeek → субтитры RU
Исходящий: Ваш микрофон  → Whisper (RU) → DeepSeek → Edge TTS (EN) → BlackHole → Steam
```

## Требования

- macOS
- Python 3.9+
- [BlackHole](https://existential.audio/blackhole/) (бесплатный виртуальный аудиокабель)
- API-ключ [DeepSeek](https://platform.deepseek.com/)

## Установка

```bash
cd translate
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Вставьте DEEPSEEK_API_KEY в .env
```

## Настройка аудио для CS2 (macOS)

### 1. Установите BlackHole 2ch

Скачайте с [existential.audio/blackhole](https://existential.audio/blackhole/).

### 2. Multi-Output для звука игры

1. Откройте **Audio MIDI Setup**
2. **+** → **Create Multi-Output Device**
3. Включите **BlackHole 2ch** + ваши **наушники**
4. В системных настройках звука выберите Multi-Output как устройство вывода

Так вы слышите игру, а приложение захватывает голос команды через BlackHole.

### 3. Виртуальный микрофон для Steam

1. В `.env` укажите **BlackHole output** как `VIRTUAL_MIC_DEVICE`
2. В **Steam → Settings → Voice → Voice Input Device** выберите **BlackHole 2ch**
3. Говорите в **реальный микрофон** — приложение переводит и отправляет английский голос в BlackHole, Steam его транслирует

### 4. Найдите индексы устройств

```bash
python -m src.main --list-devices
```

Пример `.env`:

```
TEAM_AUDIO_DEVICE=2    # BlackHole input (голос команды из игры)
MIC_INPUT_DEVICE=0     # Ваш микрофон
VIRTUAL_MIC_DEVICE=3   # BlackHole output (Steam mic)
```

### 5. CS2 / Steam

- CS2 в **оконном** или **borderless** режиме — иначе оверлей может не быть виден
- Voice chat включён в CS2
- **Push-to-talk** в Steam рекомендуется — меньше лишнего перевода

## Запуск

```bash
source .venv/bin/activate
python -m src.main
```

- Субтитры команды — белым, ваш перевод — голубым
- **Escape** — выход
- Первый запуск скачает модели Whisper (~150 MB + ~460 MB)

## Настройки (.env)

| Переменная | Описание |
|------------|----------|
| `DEEPSEEK_API_KEY` | Ключ API DeepSeek |
| `TEAM_AUDIO_DEVICE` | BlackHole input — голос команды |
| `MIC_INPUT_DEVICE` | Ваш микрофон (по умолчанию — системный) |
| `VIRTUAL_MIC_DEVICE` | BlackHole output — виртуальный мик для Steam |
| `WHISPER_MODEL_IN` | Модель для EN (`small.en` рекомендуется) |
| `WHISPER_MODEL_OUT` | Модель для RU (`small` — мультиязычная) |
| `TTS_VOICE` | Голос Edge TTS (`en-US-GuyNeural`, `en-US-JennyNeural`) |
| `ENABLE_OUTGOING` | Включить RU→EN (`true`/`false`) |
| `SHOW_ORIGINAL` | Показывать английский над субтитрами |

## Советы для CS2

- Говорите **коротко**: «Раш B», «Флеш», «Один на A»
- `small.en` + `small` — баланс скорости и качества
- Задержка исходящего ~2–4 сек — используйте push-to-talk
- Если команда не слышит вас — проверьте `VIRTUAL_MIC_DEVICE` и микрофон в Steam

## Дорожная карта

- [x] EN → RU субтитры (оверлей)
- [x] RU → EN голос в виртуальный микрофон
- [ ] Горячие клавиши, настройка позиции оверлея
- [ ] Игровой словарь CS2
