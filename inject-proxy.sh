#!/bin/bash
UPSTREAM="https://sub.envymoon.space$1"
USER_AGENT="$2"

# Получить оригинальную подписку
ORIGINAL=$(curl -s "$UPSTREAM")

# Если User-Agent содержит hiddify/nekobox/etc - добавить наши ссылки
if echo "$USER_AGENT" | grep -qiE "hiddify|happ|nekobox|nekoray|sing-box|v2rayng|v2rayn|v2raytun"; then
    # Декодировать оригинал
    DECODED=$(echo "$ORIGINAL" | base64 -d)
    # Добавить наши ссылки
    INJECT=$(cat /opt/remna-sub-injector/data/links.txt)
    # Закодировать обратно
    echo -e "${DECODED}\n${INJECT}" | base64 -w0
else
    echo "$ORIGINAL"
fi
