#!/bin/bash

# Function to kill any process using port 5000
kill_process_on_port() {
    PORT=5000
    PIDS=$(lsof -ti :$PORT)
    if [ -n "$PIDS" ]; then
        echo "Killing process(es) on port $PORT: $PIDS"
        echo "$PIDS" | xargs -n 1 kill -9
    else
        echo "No process found on port $PORT"
    fi
}

# Kill the process using port 5000, if any
kill_process_on_port

# Run the Python application
python app.py &

# Wait for a few seconds to ensure the server starts
sleep 2

# Open the URL in the default web browser
if which xdg-open > /dev/null
then
  xdg-open http://127.0.0.1:5000
elif which gnome-open > /dev/null
then
  gnome-open http://127.0.0.1:5000
elif which open > /dev/null
then
  open http://127.0.0.1:5000
else
  echo "Could not detect the web browser to use."
fi