import json
import subprocess
from pathlib import Path

from fastapi import HTTPException


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """
    外部コマンドを安全に実行するための共通関数。
    今後 ffmpeg / ffprobe / OpenSfM などを呼び出すときにも使う。
    """
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Command not found: {command[0]}",
        ) from error
    except subprocess.CalledProcessError as error:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Command failed: {command[0]}",
                "stdout": error.stdout,
                "stderr": error.stderr,
            },
        ) from error


def get_video_info(video_path: Path) -> dict:
    """
    ffprobe を使って動画ファイルの基本情報を取得する。
    """
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]

    result = run_command(command)
    raw_info = json.loads(result.stdout)

    video_stream = None
    for stream in raw_info.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    if video_stream is None:
        raise HTTPException(status_code=400, detail="No video stream found")

    width = video_stream.get("width")
    height = video_stream.get("height")
    codec_name = video_stream.get("codec_name")
    avg_frame_rate = video_stream.get("avg_frame_rate", "0/0")

    duration = raw_info.get("format", {}).get("duration")
    size = raw_info.get("format", {}).get("size")

    return {
        "path": str(video_path),
        "filename": video_path.name,
        "width": width,
        "height": height,
        "codec_name": codec_name,
        "avg_frame_rate": avg_frame_rate,
        "duration_sec": float(duration) if duration is not None else None,
        "size_bytes": int(size) if size is not None else None,
    }