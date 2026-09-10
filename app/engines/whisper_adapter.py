from whisper_processor import (
    describe_whisper_configuration,
    load_whisper_model,
    transcribe_audio,
    transcribe_audio_with_model,
)
from services.gpu_stage_scheduler import GPUStageScheduler


class WhisperAdapter:
    def transcribe(self, audio_path: str, model_path: str, *, language: str = "auto", task: str = "transcribe"):
        with GPUStageScheduler.stage("whisper"):
            return transcribe_audio(audio_path, model_path, language=language, task=task)

    def load_model(self, model_path: str):
        return load_whisper_model(model_path)

    def configuration(self, model_path: str, *, language: str, model=None, use_batched: bool = True):
        return describe_whisper_configuration(
            model_path,
            language=language,
            model=model,
            use_batched=use_batched,
        )

    def transcribe_with_model(self, model, audio_path: str, *, language: str = "auto", task: str = "transcribe", use_batched: bool = True):
        with GPUStageScheduler.stage("whisper"):
            return transcribe_audio_with_model(
                model,
                audio_path,
                language=language,
                task=task,
                use_batched=use_batched,
                model_path=str(getattr(model, "_capcap_model_name", "") or ""),
            )
