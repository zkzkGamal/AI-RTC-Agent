#!/bin/bash

ENV_FILE=".env"

options=("general" "hr" "developer" "research")

selected=0

draw_menu() {
    clear
    echo "Select AGENT_MODE:"
    echo ""

    for i in "${!options[@]}"; do
        if [ $i -eq $selected ]; then
            echo -e "\e[7m> ${options[$i]}\e[0m"
        else
            echo "  ${options[$i]}"
        fi
    done
}

while true; do
    draw_menu

    read -rsn1 key

    if [[ $key == $'\x1b' ]]; then
        read -rsn2 key2

        case "$key2" in
            "[A") ((selected--));;
            "[B") ((selected++));;
        esac

        # wrap around
        if [ $selected -lt 0 ]; then
            selected=$((${#options[@]} - 1))
        fi
        if [ $selected -ge ${#options[@]} ]; then
            selected=0
        fi

    elif [[ $key == "" ]]; then
        break
    fi
done

choice=${options[$selected]}

echo ""
echo "Selected: $choice"

# -----------------------------
# UPDATE .env FILE
# -----------------------------

if grep -q "^AGENT_MODE=" "$ENV_FILE"; then
    # replace existing value
    sed -i "s/^AGENT_MODE=.*/AGENT_MODE=$choice/" "$ENV_FILE"
else
    # add if not exists
    echo "AGENT_MODE=$choice" >> "$ENV_FILE"
fi

echo "Updated .env successfully!"