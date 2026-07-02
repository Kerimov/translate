"""Тест исходящего перевода: ваш микрофон → RU → EN → озвучка."""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sounddevice as sd

from src.audio import AudioCapture
from src.config import Settings
from src.stt import SpeechToText
from src.translate import Translator
from src.tts import TextToSpeech


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Тест: что услышит команда (RU → EN → голос)"
    )
    parser.add_argument(
        "--cable",
        action="store_true",
        help="Отправить звук в VB-Cable (как в Steam), иначе — в наушники",
    )
    parser.add_argument(
        "--text",
        help='Быстрый тест без микрофона, например: --text "Раш Б, двое на A"',
    )
    args = parser.parse_args()

    settings = Settings.load()
    if not settings.deepseek_api_key:
        print("Ошибка: укажите DEEPSEEK_API_KEY в .env")
        sys.exit(1)

    if args.cable:
        output_device = settings.virtual_mic_device
        output_label = f"VB-Cable [{output_device}]"
    else:
        output_device = sd.default.device[1]
        output_label = f"наушники [{output_device}]"

    translator = Translator(settings.deepseek_api_key)
    tts = TextToSpeech(settings.tts_voice, output_device)

    def process_phrase(ru_text: str) -> None:
        print(f"\nВы сказали:     {ru_text}")
        en_text = translator.translate(ru_text, direction="ru_to_en")
        print(f"Команда услышит: {en_text}")
        print(f"Озвучиваю -> {output_label}")
        tts.speak(en_text)
        print("-" * 40)

    if args.text:
        process_phrase(args.text)
        translator.close()
        return

    stt = SpeechToText(settings.whisper_model_out, label="test-stt")
    lock = threading.Lock()

    def on_segment(audio) -> None:
        if not lock.acquire(blocking=False):
            print("[пропуск] ещё обрабатывается предыдущая фраза")
            return

        def work() -> None:
            try:
                text = stt.transcribe(audio, language="ru")
                if text:
                    process_phrase(text)
            except Exception as exc:
                print(f"[ошибка] {exc}")
            finally:
                lock.release()

        threading.Thread(target=work, daemon=True).start()

    print("=== Тест исходящего перевода ===")
    print(f"Микрофон:  [{settings.mic_input_device}]")
    print(f"Вывод:     {output_label}")
    print("Говорите по-русски короткими фразами (как в CS2). Ctrl+C — выход.\n")

    capture = AudioCapture(
        on_segment,
        device=settings.mic_input_device,
        label="test-mic",
        silence_frames=settings.segment_silence_frames,
        min_speech_frames=settings.segment_min_speech_frames,
    )
    capture.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nВыход.")
    finally:
        capture.stop()
        translator.close()


if __name__ == "__main__":
    main()
