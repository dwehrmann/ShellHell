#!/bin/bash

# Test script to run the game with automated input and capture output

echo "Starting game test..."
echo ""

# Send commands: start, confirm rolls, choose race, enter name, try a free action
(
  sleep 0.5
  echo "s"           # start
  sleep 0.5
  echo "b"           # bestätigen (confirm rolls)
  sleep 0.5
  echo "m"           # Mensch (human race)
  sleep 0.5
  echo "TestHero"    # name
  sleep 1
  echo "untersuche den raum"  # free action
  sleep 2
  echo "q"           # quit
) | timeout 10 venv/bin/python main.py 2>&1 | tee /tmp/game_output.txt

echo ""
echo "========================================"
echo "Game output saved to /tmp/game_output.txt"
echo "Checking for errors..."
grep -i "fehler\|error\|exception" /tmp/game_output.txt || echo "No errors found"
echo ""
echo "Checking for free action..."
grep -i "untersuche\|plausibil" /tmp/game_output.txt || echo "Free action not found in output"
