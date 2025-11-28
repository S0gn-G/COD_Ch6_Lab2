#!/usr/bin/env bash
set -euo pipefail

echo "[DEBUG] 启动 ISPC 安装脚本..."

########################################
# 0. 检查下载工具
########################################

if command -v curl >/dev/null 2>&1; then
    DL=curl
    echo "[DEBUG] 将使用 curl 下载"
elif command -v wget >/dev/null 2>&1; then
    DL=wget
    echo "[DEBUG] 将使用 wget 下载"
else
    echo "错误：需要 curl 或 wget" >&2
    exit 1
fi

########################################
# 1. 获取版本号：若未指定，则自动抓最新
########################################

if [[ -z "${ISPC_VERSION:-}" ]]; then
    echo "[DEBUG] 未发现 ISPC_VERSION，尝试自动检测最新版本..."

    if [[ "$DL" == curl ]]; then
        url=$(curl -Ls -o /dev/null -w '%{url_effective}' https://github.com/ispc/ispc/releases/latest || true)
        ISPC_VERSION="${url##*/}"
    else
        html=$(wget -qO- https://github.com/ispc/ispc/releases/latest || true)
        ISPC_VERSION=$(echo "$html" | grep -o 'tag/v[^"]*' | sed 's#tag/##' | head -n1)
    fi

    if [[ -z "$ISPC_VERSION" ]]; then
        echo "[DEBUG] 自动检测失败，使用默认版本 v1.22.0"
        ISPC_VERSION="v1.22.0"
    fi
fi

echo "[DEBUG] 使用 ISPC 版本: $ISPC_VERSION"

########################################
# 2. 判断系统与架构
########################################

OS=$(uname -s)
ARCH=$(uname -m)

echo "[DEBUG] 系统 uname -s: $OS"
echo "[DEBUG] 系统 uname -m: $ARCH"

SUFFIX=""

case "$OS" in
    Linux)
        case "$ARCH" in
            x86_64|amd64) SUFFIX="linux";;
            aarch64|arm64) SUFFIX="linux-aarch64";;
            *) echo "错误：不支持的 Linux 架构: $ARCH"; exit 1;;
        esac
        ;;
    Darwin)
        case "$ARCH" in
            x86_64)
                SUFFIX="macOS"
                ;;
            arm64)
                if [[ "${ISPC_USE_UNIVERSAL_MACOS:-0}" == "1" ]]; then
                    SUFFIX="macOS-universal"
                else
                    SUFFIX="macOS-arm64"
                fi
                ;;
            *)
                echo "错误：不支持的 macOS 架构: $ARCH"; exit 1;;
        esac
        ;;
    *)
        echo "错误：不支持的操作系统: $OS"
        exit 1
        ;;
esac

echo "[DEBUG] 选择包后缀: $SUFFIX"

########################################
# 3. 构造下载 URL
########################################

TAR="ispc-${ISPC_VERSION}-${SUFFIX}.tar.gz"
URL="https://github.com/ispc/ispc/releases/download/${ISPC_VERSION}/${TAR}"

echo "[DEBUG] 下载 URL: $URL"
echo "[DEBUG] 目标压缩包: $TAR"

########################################
# 4. 下载 & 校验
########################################

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"

echo "[DEBUG] 临时目录: $tmp"

if [[ "$DL" == curl ]]; then
    echo "[DEBUG] curl 下载中..."
    curl -L --retry 3 --retry-delay 2 "$URL" -o "$TAR" || {
        echo "错误：curl 下载失败" >&2
        exit 1
    }
else
    echo "[DEBUG] wget 下载中..."
    wget --tries=3 "$URL" -O "$TAR" || {
        echo "错误：wget 下载失败" >&2
        exit 1
    }
fi

echo "[DEBUG] 下载完成"

# 校验大小
SIZE=$(stat -c%s "$TAR" 2>/dev/null || stat -f%z "$TAR")
echo "[DEBUG] 下载文件大小: $SIZE bytes"

if [[ "$SIZE" -lt 1000000 ]]; then
    echo "错误：下载的文件过小（<1MB），很可能是 GitHub 错误页面" >&2
    exit 1
fi

# 校验 gzip 格式
if command -v file >/dev/null 2>&1; then
    TYPE=$(file "$TAR")
    echo "[DEBUG] file 类型: $TYPE"
    if ! echo "$TYPE" | grep -q "gzip compressed"; then
        echo "错误：下载文件不是 gzip 格式，可能是 HTML 错误页面" >&2
        exit 1
    fi
fi

# tar 能否正常列出内容
echo "[DEBUG] 检查 tar 内容..."
if ! tar -tzf "$TAR" >/dev/null 2>&1; then
    echo "错误：tar 包损坏或格式错误" >&2
    exit 1
fi

echo "[DEBUG] tar 包校验通过"

########################################
# 5. 安装
########################################

INSTALL_ROOT="$HOME/.local"
INSTALL_DIR="$INSTALL_ROOT/ispc/bin"
BIN_DIR="$INSTALL_ROOT/bin"

echo "[DEBUG] 安装目录: $INSTALL_DIR"
echo "[DEBUG] bin 目录: $BIN_DIR"

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo "[DEBUG] 解压中..."
tar -xzf "$TAR" -C "$INSTALL_DIR" --strip-components=1

echo "[DEBUG] 创建软链接..."
ln -sf "$INSTALL_DIR/ispc" "$BIN_DIR/ispc"

########################################
# 6. rc 文件写 PATH
########################################

case "$(basename ${SHELL:-bash})" in
    zsh) RC="$HOME/.zshrc" ;;
    *)   RC="$HOME/.bashrc" ;;
esac

echo "[DEBUG] 使用 RC 文件: $RC"

if [[ ! -f "$RC" ]]; then
    echo "[DEBUG] RC 文件不存在，创建: $RC"
    touch "$RC"
fi

if ! grep -q 'HOME/.local/bin' "$RC" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC"
    echo "[DEBUG] 已写入 PATH 到 $RC"
else
    echo "[DEBUG] $RC 已存在 PATH 设置，跳过"
fi

########################################
# 7. 完成
########################################

echo "================================="
echo "ISPC 安装成功"
echo "版本: $ISPC_VERSION"
echo "平台: $OS / $ARCH"
echo "安装路径: $INSTALL_DIR"
echo "请执行：source $RC"
echo "然后运行：ispc --version"
echo "================================="