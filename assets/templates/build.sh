#!/bin/sh
# One-command rebuild. Run from the project folder with Git Bash / sh.
#   LIB=/path/to/lemo-opuscar PY=/path/to/python sh build.sh
set -eu

PROJ=$(cd "$(dirname "$0")" && pwd)
cd "$PROJ"

[ -f project.env ] || { echo "build.sh: project.env missing" >&2; exit 1; }
. "$PROJ/project.env"

: "${SLUG:?project.env needs SLUG}"
: "${SONG:?project.env needs SONG}"
: "${DUR:?project.env needs DUR}"
: "${FPS:?project.env needs FPS}"
: "${WIDTH:?project.env needs WIDTH}"
: "${HEIGHT:?project.env needs HEIGHT}"
: "${POSTER_T:?project.env needs POSTER_T}"
: "${COVER_SHAPES:=4x3,3x4}"

PY=${PY:-}
FF=${FF:-ffmpeg}
WORKERS=${WORKERS:-3}

if [ -z "${LIB:-}" ]; then
  for d in "$PROJ/../lemo-opuscar" "$HOME/lemo-opuscar"; do
    if [ -f "$d/core/render/video.mjs" ]; then LIB="$d"; break; fi
  done
fi
[ -n "${LIB:-}" ] || {
  echo "build.sh: set LIB to the lemo-opuscar library (contains core/render/video.mjs)" >&2
  exit 1
}
[ -f "$LIB/core/render/video.mjs" ] || { echo "build.sh: bad LIB: $LIB" >&2; exit 1; }
if [ -z "${PY:-}" ]; then
  for p in "$LIB/.venv/bin/python" "$LIB/.venv/Scripts/python.exe"; do
    if [ -x "$p" ] && "$p" -c 'import numpy, scipy, soundfile' >/dev/null 2>&1; then
      PY=$p; break
    fi
  done
fi
PY=${PY:-python3}
command -v node >/dev/null 2>&1 || { echo "build.sh: node is not on PATH" >&2; exit 1; }
command -v "$PY" >/dev/null 2>&1 || [ -x "$PY" ] || { echo "build.sh: python not found: $PY" >&2; exit 1; }
command -v "$FF" >/dev/null 2>&1 || [ -x "$FF" ] || { echo "build.sh: ffmpeg not found: $FF" >&2; exit 1; }

case "$SONG" in
  /*|[A-Za-z]:*) ;;
  *) SONG="$PROJ/$SONG" ;;
esac
[ -f "$SONG" ] || { echo "build.sh: source song missing: $SONG" >&2; exit 1; }

case "$FF" in
  */*|*\\*)
    # Git Bash mangles "E:/..." when it is put on PATH; use the POSIX form.
    FF_DIR=$(cd "$(dirname "$FF")" && pwd)
    PATH="$FF_DIR:$PATH"; export PATH
    ;;
esac

mkdir -p audio out stills analysis

echo "[1/10] decode song"
if [ ! -f audio/song.wav ] || [ "$SONG" -nt audio/song.wav ]; then
  "$FF" -y -loglevel error -i "$SONG" -vn -ac 2 -ar 48000 -c:a pcm_s16le audio/song.wav
fi

echo "[2/10] bake CJK glyphs"
"$PY" "$PROJ/tools/genfont.py" "$PROJ"

echo "[3/10] mix song, beds and foley"
"$PY" "$PROJ/tools/mix.py" "$PROJ"

echo "[4/10] master to -14 LUFS / -1.2 dBTP"
"$PY" "$PROJ/tools/master_audio.py" "$PROJ/audio/mix.wav" "$PROJ/audio/master.wav" --ffmpeg "$FF"

echo "[5/10] caption check (one line, overlay layer)"
node "$PROJ/tools/check_subs.js" "$PROJ"

echo "[6/10] subtitles from the same caption segments"
node "$PROJ/tools/caption_segments.js" "$PROJ" --out "$PROJ/out/segments.json"
"$PY" "$PROJ/tools/make_srt.py" "$PROJ" --segments "$PROJ/out/segments.json" --out "$PROJ/$SLUG.srt"

echo "[7/10] render $DUR s at $FPS fps"
node "$LIB/core/render/video.mjs" "$PROJ" --fps "$FPS" --workers "$WORKERS" \
  --size "${WIDTH}x${HEIGHT}" --out "$PROJ/out/video.mp4"

echo "[8/10] mux"
"$FF" -y -loglevel error -i "$PROJ/out/video.mp4" -i "$PROJ/audio/master.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -ac 2 \
  -movflags +faststart -shortest "$PROJ/$SLUG.mp4"

echo "[9/10] poster"
node "$LIB/core/render/still.mjs" "$PROJ" "$POSTER_T" --prefix poster_
[ -f "$PROJ/stills/poster_$POSTER_T.jpg" ] || {
  echo "build.sh: poster still missing: stills/poster_$POSTER_T.jpg" >&2
  exit 1
}
cp "$PROJ/stills/poster_$POSTER_T.jpg" "$PROJ/poster.jpg"

echo "[10/10] designed 4:3 and 3:4 covers (own grids, song title set in)"
"$PY" "$PROJ/tools/make_covers.py" "$PROJ" --lib "$LIB" --node node --ffmpeg "$FF" \
  --shapes "${COVER_SHAPES:-4x3,3x4}"

echo
ls -lh "$PROJ/$SLUG.mp4" "$PROJ/poster.jpg" \
  "$PROJ/cover_4x3.jpg" "$PROJ/cover_3x4.jpg" "$PROJ/$SLUG.srt"
echo "done: $PROJ/$SLUG.mp4"
