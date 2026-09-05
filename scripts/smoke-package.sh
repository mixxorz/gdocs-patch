#!/usr/bin/env bash
set -euo pipefail

package=$1
root=$PWD
dist="$root/dist/$package"
base="$root/.smoke/$package-base"
mcp="$root/.smoke/$package-mcp"
module=${package//-/_}
token_var=$(printf '%s_MCP_TOKEN' "$module" | tr '[:lower:]' '[:upper:]')

uv build --package "$package" --out-dir "$dist"
uv run twine check --strict "$dist"/*
sdist=("$dist"/*.tar.gz)
uv build "${sdist[0]}" --wheel --out-dir "$dist/from-sdist"
wheel=("$dist/from-sdist"/*.whl)
uv venv --clear --python 3.14 "$base"
uv pip install --python "$base/bin/python" "${wheel[0]}"
uv venv --clear --python 3.14 "$mcp"
uv pip install --python "$mcp/bin/python" "${wheel[0]}[mcp]"

cd "$root/.smoke"
"$base/bin/$package" --help >/dev/null
"$base/bin/$package" --version
if output=$("$base/bin/$package-mcp" 2>&1); then
    echo "$package-mcp unexpectedly started without the MCP extra" >&2
    exit 1
fi
grep -F "MCP support is not installed" <<<"$output"
"$mcp/bin/$package-mcp" --help >/dev/null
env "$token_var=smoke-test" "$mcp/bin/python" -I -c "import $module.mcp_server.server"
if [[ "$package" == gsheets-patch ]]; then
    "$base/bin/$package" schema RepeatCellRequest >/dev/null
fi
