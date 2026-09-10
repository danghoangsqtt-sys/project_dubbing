import os
import tempfile

from core.models import coerce_segments

def format_timestamp(seconds):
    """
    Converts seconds to SRT timestamp format: HH:MM:SS,mmm
    """
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

def generate_srt(segments, output_path, max_gap_ms=100.0):
    """
    Converts segments list to an SRT file.

    Args:
        segments (list): List of dicts (or Segment models) with
            'start', 'end', 'text'.
        output_path (str): Path to save the .srt file.
        max_gap_ms (float): Maximum gap in milliseconds to close between
            consecutive segments. Default is 100ms.
    """
    normalized_segments = coerce_segments(segments)
    max_gap_s = max_gap_ms / 1000.0
    target = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(target)}.", suffix=".tmp", dir=os.path.dirname(target)
    )
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as f:
            for i, seg in enumerate(normalized_segments, 1):
                start = format_timestamp(seg.start)
                end_time = seg.end
                
                # Close small gaps to next segment
                if i < len(normalized_segments):
                    next_seg = normalized_segments[i]
                    gap = next_seg.start - end_time
                    if 0 < gap <= max_gap_s:
                        end_time = next_seg.start
                
                end = format_timestamp(end_time)
                text = seg.subtitle_text

                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, target)
    except BaseException:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
    print("Subtitle generated successfully.")
    return True

if __name__ == "__main__":
    # Test
    test_segments = [
        {'start': 0.0, 'end': 2.5, 'text': 'Hello world'},
        {'start': 2.6, 'end': 5.0, 'text': 'This is a test subtitle'}
    ]
    generate_srt(test_segments, "test.srt")
