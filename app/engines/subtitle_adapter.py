from subtitle_builder import generate_srt


class SubtitleAdapter:
    def generate_srt(self, segments, output_path: str, max_gap_ms: float = 100.0) -> str:
        if not generate_srt(segments, output_path, max_gap_ms=max_gap_ms):
            raise RuntimeError(f"Could not generate subtitle file: {output_path}")
        return output_path
