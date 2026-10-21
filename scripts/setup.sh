#!/bin/sh
# One-time setup for lyric-mv-producer.
#   sh scripts/setup.sh              check the toolchain, install Lemo-Opuscar
#   sh scripts/setup.sh --check      report only; change nothing
#   sh scripts/setup.sh --lib DIR    install the renderer at DIR
#
# This installs the renderer and its packages. It does not install Node,
# ffmpeg, Python, or a system browser.
set -eu

LIB=${LEMO_OPUSCAR_HOME:-$HOME/lemo-opuscar}
CHECK=0

usage() {
  cat <<'EOF'
usage: sh scripts/setup.sh [--check] [--lib DIR]

Checks Node 20+, ffmpeg, Python 3.11+ (or uv), then installs Lemo-Opuscar
(default: ~/lemo-opuscar) with its Node packages, headless Chromium and Python
core tier. Node, ffmpeg, Python and a system browser are not installed.

  --check     report versions and paths, change nothing
  --lib DIR   install the renderer at DIR (or set LEMO_OPUSCAR_HOME)
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check) CHECK=1 ;;
    --lib)
      [ $# -ge 2 ] || { usage >&2; exit 2; }
      LIB=$2
      shift
      ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
warn() { printf '! %s\n' "$*" >&2; }
die() { printf 'setup: %s\n' "$*" >&2; exit 1; }

node_major=0
if command -v node >/dev/null 2>&1; then
  node_major=$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)
fi

has_ffmpeg=0
command -v ffmpeg >/dev/null 2>&1 && has_ffmpeg=1

sys_py=
for c in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$c" >/dev/null 2>&1 &&
     "$c" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>/dev/null; then
    sys_py=$c
    break
  fi
done

has_uv=0
command -v uv >/dev/null 2>&1 && has_uv=1

if [ "$node_major" -ge 20 ]; then
  node_text=$(node -v 2>/dev/null)
else
  node_text="missing or older than 20"
fi
if [ "$has_ffmpeg" -eq 1 ]; then
  ff_text=$(ffmpeg -version 2>/dev/null | head -1)
else
  ff_text=missing
fi
if [ -n "$sys_py" ]; then
  py_text=$("$sys_py" -V 2>&1)" ($sys_py)"
elif [ "$has_uv" -eq 1 ]; then
  py_text="uv $(uv --version 2>/dev/null | awk '{print $2}')"
else
  py_text="missing (need 3.11+ or uv)"
fi

say "node      $node_text"
say "ffmpeg    $ff_text"
say "python    $py_text"
if [ -f "$LIB/core/render/video.mjs" ]; then
  say "renderer  $LIB"
else
  say "renderer  missing at $LIB"
fi

if [ "$CHECK" -eq 1 ]; then
  ok=1
  [ "$node_major" -ge 20 ] || ok=0
  [ "$has_ffmpeg" -eq 1 ] || ok=0
  [ -n "$sys_py" ] || [ "$has_uv" -eq 1 ] || ok=0
  [ -f "$LIB/core/render/video.mjs" ] || ok=0
  [ "$ok" -eq 1 ] || exit 1
  exit 0
fi

[ "$node_major" -ge 20 ] || die "Node 20+ is required"
[ "$has_ffmpeg" -eq 1 ] || die "ffmpeg is required and must be on PATH"
[ -n "$sys_py" ] || [ "$has_uv" -eq 1 ] || die "Python 3.11+ or uv is required"

if [ ! -f "$LIB/core/render/video.mjs" ]; then
  if [ -e "$LIB" ] && [ -n "$(ls -A "$LIB" 2>/dev/null)" ]; then
    die "$LIB exists but is not the Lemo-Opuscar library; use --lib DIR or LEMO_OPUSCAR_HOME"
  fi
  command -v git >/dev/null 2>&1 || die "git is required to download Lemo-Opuscar"
  say "downloading the renderer into $LIB"
  mkdir -p "$(dirname "$LIB")"
  git clone --quiet --depth 1 --filter=blob:none --sparse --branch main \
    https://github.com/lemomo-ai/lemo-opuscar.git "$LIB" ||
    die "could not download Lemo-Opuscar"
  git -C "$LIB" sparse-checkout set --no-cone \
    '/*' '!/styles/*/demo/' '!/styleboard/' '!/docs/frames/' \
    '!/docs/cover.jpg' '!/docs/opuscar98.jpg' '!/styles/*/poster.jpg' 2>/dev/null ||
    git -C "$LIB" sparse-checkout disable ||
    die "could not check out the renderer files"
  git -C "$LIB" config lemo.managed true
fi

# Lemo's installer expects .venv/bin/python, which Windows venvs do not create.
# Build the venv here when possible, and add the POSIX shim after it exists.
if [ ! -e "$LIB/.venv" ] && [ -n "$sys_py" ]; then
  say "creating the Python environment"
  "$sys_py" -m venv "$LIB/.venv" || die "python -m venv failed"
fi
if [ -x "$LIB/.venv/Scripts/python.exe" ] && [ ! -x "$LIB/.venv/bin/python" ]; then
  mkdir -p "$LIB/.venv/bin"
  cat > "$LIB/.venv/bin/python" <<'SH'
#!/bin/sh
exec "$(dirname "$0")/../Scripts/python.exe" "$@"
SH
  chmod +x "$LIB/.venv/bin/python"
fi

SETUP="$LIB/plugin/skills/lemo-opuscar/scripts/setup.sh"
[ -f "$SETUP" ] || die "Lemo-Opuscar setup script is missing: $SETUP"
say "installing renderer packages (a few minutes)"
LEMO_OPUSCAR_HOME="$LIB" sh "$SETUP" deps || die "renderer package install failed"

py=
for p in "$LIB/.venv/bin/python" "$LIB/.venv/Scripts/python.exe"; do
  if [ -x "$p" ] && "$p" -c 'import numpy, scipy, soundfile' >/dev/null 2>&1; then
    py=$p
    break
  fi
done
if [ -z "$py" ]; then
  for c in "$sys_py" python3 python; do
    [ -n "$c" ] || continue
    if command -v "$c" >/dev/null 2>&1 &&
       "$c" -c 'import numpy, scipy, soundfile' >/dev/null 2>&1; then
      py=$(command -v "$c")
      break
    fi
  done
fi
[ -n "$py" ] || die "numpy, scipy and soundfile are not importable; install them for your Python"

say ""
say "setup complete"
say "LIB=$LIB"
say "PY=$py"
say ""
say "Next: LIB=\"$LIB\" sh build.sh"
