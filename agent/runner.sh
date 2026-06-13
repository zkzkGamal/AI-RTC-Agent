#!/bin/bash

# AI-RTC-Agent Modern Command Center & Runner

ENV_FILE=".env"

# Colorful ASCII Logo
draw_logo() {
    local logo=(
        "  \e[1;35m███████╗██╗  ██╗███████╗██╗  ██╗\e[0m"
        "  \e[1;35m╚══███╔╝██║ ██╔╝╚══███╔╝██║ ██╔╝\e[0m"
        "  \e[1;36m  ███╔╝ █████╔╝   ███╔╝ █████╔╝ \e[0m"
        "  \e[1;36m ███╔╝  ██╔═██╗  ███╔╝  ██╔═██╗ \e[0m"
        "  \e[1;34m███████╗██║  ██╗███████╗██║  ██╗\e[0m"
        "  \e[1;34m╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝\e[0m"
    )
    for line in "${logo[@]}"; do
        echo -e "$line"
        sleep 0.03
    done
}

# Spinner loading animation
show_loading() {
    local duration=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local count=${#spin}
    local start_time=$(date +%s)
    local end_time=$((start_time + duration))
    
    echo -ne "\e[1;33m"
    while [ $(date +%s) -lt $end_time ]; do
        for ((i=0; i<count; i++)); do
            echo -ne "\r  ${spin:$i:1}  $message..."
            sleep 0.06
        done
    done
    echo -e "\r  \e[1;32m✔  $message completed!\e[0m"
}

# Reusable keyboard-controlled menu
select_menu() {
    local title=$1
    shift
    local options=("$@")
    local selected=0
    local key=""
    local num_options=${#options[@]}

    draw_menu() {
        clear
        draw_logo
        echo -e "\n\e[1;35m▶ $title\e[0m"
        echo -e "\e[1;30mUse Up/Down Arrow keys and press Enter to select\e[0m\n"
        
        for i in "${!options[@]}"; do
            if [ $i -eq $selected ]; then
                echo -e "  \e[1;36m➤  \e[1;46;30m ${options[$i]} \e[0m"
            else
                echo -e "     \e[1;37m${options[$i]}\e[0m"
            fi
        done
        echo ""
    }

    # Hide cursor
    echo -ne "\e[?25l"

    while true; do
        draw_menu
        read -rsn1 key
        
        if [[ $key == $'\x1b' ]]; then
            read -rsn2 key2
            case "$key2" in
                "[A") # Up
                    ((selected--))
                    if [ $selected -lt 0 ]; then
                        selected=$((num_options - 1))
                    fi
                    ;;
                "[B") # Down
                    ((selected++))
                    if [ $selected -ge $num_options ]; then
                        selected=0
                    fi
                    ;;
            esac
        elif [[ $key == "" ]]; then
            break
        fi
    done

    # Restore cursor
    echo -ne "\e[?25h"
    return $selected
}

# -----------------------------
# STEP 1: SELECT AGENT_MODE
# -----------------------------
mode_options=("general" "hr" "developer" "research")
select_menu "Select AGENT_MODE:" "${mode_options[@]}"
mode_idx=$?
mode_val=${mode_options[$mode_idx]}

# -----------------------------
# STEP 2: SELECT AGENT_TYPE
# -----------------------------
type_options=("api" "chat" "test")
select_menu "Select AGENT_TYPE:" "${type_options[@]}"
type_idx=$?
type_val=${type_options[$type_idx]}

clear
draw_logo
echo ""

# Ensure .env exists
touch "$ENV_FILE"

# Update AGENT_MODE in .env
if grep -q "^AGENT_MODE=" "$ENV_FILE"; then
    sed -i "s/^AGENT_MODE=.*/AGENT_MODE=$mode_val/" "$ENV_FILE"
else
    echo "AGENT_MODE=$mode_val" >> "$ENV_FILE"
fi

# Update AGENT_TYPE in .env
if grep -q "^AGENT_TYPE=" "$ENV_FILE"; then
    sed -i "s/^AGENT_TYPE=.*/AGENT_TYPE=$type_val/" "$ENV_FILE"
else
    echo "AGENT_TYPE=$type_val" >> "$ENV_FILE"
fi

# -----------------------------
# STEP 3: RUN AGENT BASED ON TYPE
# -----------------------------
if [ "$type_val" = "api" ]; then
    # Interactive prompt for Port & Workers
    echo -e "\e[1;36m┌──────────────────────────────────────────────┐\e[0m"
    echo -e "\e[1;36m│\e[0m  Configure API server settings:              \e[1;36m│\e[0m"
    echo -e "\e[1;36m└──────────────────────────────────────────────┘\e[0m"
    
    echo -ne "\e[1;35m▶ Enter port number [default: 8001]: \e[0m"
    read -r port
    if [ -z "$port" ]; then
        port=8001
    fi
    
    echo -ne "\e[1;35m▶ Enter number of workers [default: 1]: \e[0m"
    read -r workers
    if [ -z "$workers" ]; then
        workers=1
    fi
    
    clear
    draw_logo
    echo ""
    show_loading 1 "Spinning up API server with $workers workers on port $port"
    echo -e "\n\e[1;32m🚀 Starting Uvicorn API Server...\e[0m\n"
    exec uvicorn main:socket_app --host 0.0.0.0 --port "$port" --workers "$workers"

elif [ "$type_val" = "chat" ]; then
    show_loading 1 "Loading chat environment"
    echo -e "\n\e[1;32m🚀 Launching CLI Chat...\e[0m\n"
    exec python main.py chat

elif [ "$type_val" = "test" ]; then
    # Scan tests directory
    tests_dir="tests"
    if [ ! -d "$tests_dir" ]; then
        echo -e "\e[1;31mError: tests/ directory not found!\e[0m"
        exit 1
    fi
    
    test_files=()
    for f in $(ls "$tests_dir"/test_*.py 2>/dev/null); do
        test_files+=("$(basename "$f")")
    done
    
    if [ ${#test_files[@]} -eq 0 ]; then
        echo -e "\e[1;31mNo test files found in tests/ directory!\e[0m"
        exit 1
    fi
    
    test_files+=("Cancel")
    
    select_menu "Select a test file to run:" "${test_files[@]}"
    test_idx=$?
    selected_test=${test_files[$test_idx]}
    
    if [ "$selected_test" = "Cancel" ]; then
        echo "Exiting."
        exit 0
    fi
    
    clear
    draw_logo
    echo ""
    show_loading 1 "Preparing test runner for $selected_test"
    echo -e "\n\e[1;32m🚀 Running test: \e[1;33m$selected_test\e[0m...\n"
    exec python tests/"$selected_test"
fi
