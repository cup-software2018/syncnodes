#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/.local/lib/syncnodes"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Installing Python dependencies..."
pip install --user -q -r "$SRC_DIR/requirements.txt"

echo "==> Copying project files to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp "$SRC_DIR/syncnodes" "$SRC_DIR/nodectl" "$SRC_DIR/copyctl" \
   "$SRC_DIR/utils.py" "$SRC_DIR/requirements.txt" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/syncnodes" "$INSTALL_DIR/nodectl" "$INSTALL_DIR/copyctl"

# Copy nodes.yml.example if no nodes.yml exists yet
if [ ! -f "$INSTALL_DIR/nodes.yml" ]; then
    cp "$SRC_DIR/nodes.yml.example" "$INSTALL_DIR/nodes.yml.example"
fi

echo "==> Installing icon..."
mkdir -p "$ICONS_DIR"
cp "$SRC_DIR/syncnodes.svg" "$ICONS_DIR/syncnodes.svg"

echo "==> Installing desktop entry..."
mkdir -p "$APPS_DIR"
sed "s|SYNCNODES_EXEC|python3 $INSTALL_DIR/syncnodes|g" \
    "$SRC_DIR/syncnodes.desktop" > "$APPS_DIR/syncnodes.desktop"

echo "==> Creating CLI symlinks in $BIN_DIR..."
mkdir -p "$BIN_DIR"
ln -sf "$INSTALL_DIR/syncnodes" "$BIN_DIR/syncnodes"
ln -sf "$INSTALL_DIR/nodectl"   "$BIN_DIR/nodectl"
ln -sf "$INSTALL_DIR/copyctl"   "$BIN_DIR/copyctl"

echo "==> Updating desktop database..."
update-desktop-database "$APPS_DIR" 2>/dev/null || true
gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "Done! syncnodes installed."
echo "  GUI:  syncnodes  (or launch from the GNOME app grid)"
echo "  CLI:  nodectl -i nodes.yml -c 'uptime'"
echo "        copyctl -i nodes.yml -s ./file -d /remote/path"
echo ""
echo "  Edit nodes: $INSTALL_DIR/nodes.yml"
