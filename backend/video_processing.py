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
def create_ocr_master(input_video_path: Path, output_video_path: Path) -> None:
    """
    OCR用の動画を作成する。
    MVP段階では、元動画を大きく変換せず、扱いやすいMP4としてコピー/再エンコードする。
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-an",
        str(output_video_path),
    ]

    run_command(command)


def create_slam_erp(input_video_path: Path, output_video_path: Path) -> None:
    """
    SLAM/OpenSfM用の軽量動画を作成する。
    360度ERP動画を、まずは横1920pxに縮小する。
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video_path),
        "-vf",
        "scale=1920:-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-an",
        str(output_video_path),
    ]

    run_command(command)


def extract_keyframes(
    input_video_path: Path,
    output_dir: Path,
    interval_sec: int = 1,
) -> None:
    """
    代表フレームを interval_sec 秒ごとに抽出する。
    初期実装では1秒ごとにJPGを保存する。
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = output_dir / "frame_%06d.jpg"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video_path),
        "-vf",
        f"fps=1/{interval_sec}",
        "-q:v",
        "2",
        str(output_pattern),
    ]

    run_command(command)


def preprocess_video_files(
    input_video_path: Path,
    derived_dir: Path,
    keyframes_dir: Path,
    interval_sec: int = 1,
) -> dict:
    """
    動画前処理の本体。
    - OCR用動画
    - SLAM用軽量動画
    - 代表フレーム
    を作成する。
    """
    derived_dir.mkdir(parents=True, exist_ok=True)
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    ocr_master_path = derived_dir / "ocr_master.mp4"
    slam_erp_path = derived_dir / "slam_erp.mp4"

    create_ocr_master(input_video_path, ocr_master_path)
    create_slam_erp(input_video_path, slam_erp_path)
    extract_keyframes(input_video_path, keyframes_dir, interval_sec=interval_sec)

    keyframe_paths = sorted(keyframes_dir.glob("frame_*.jpg"))

    return {
        "ocr_master_path": str(ocr_master_path),
        "slam_erp_path": str(slam_erp_path),
        "keyframes_dir": str(keyframes_dir),
        "keyframe_count": len(keyframe_paths),
    }