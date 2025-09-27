#! /bin/bash

# Read in flag from command line "laptop" or "jetbot"
if [ "$1" == "laptop" ]; then
    # Start the ADK API
    echo "Starting ADK API on laptop"
    cd /backend || exit 1
    source .venv/bin/activate
    pip install -r requirements.txt
    adk run root_agent &

    # Start the frontend
    echo "Starting frontend on laptop"
    cd ./frontend || exit 1
    pnpm install
    pnpm run dev
elif [ "$1" == "jetbot" ]; then
    # Start the JetBot Robot API
    echo "Starting JetBot Robot API on jetbot"
    cd ./jetbot-api || exit 1
    source .venv/bin/activate
    pip install -r requirements.txt
    python3 main.py
else
    echo "Usage: $0 [laptop|jetbot]"
    exit 1
fi
