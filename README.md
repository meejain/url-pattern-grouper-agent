# URL Pattern Grouper

[![Run URL Pattern Grouper](https://github.com/meejain/url-pattern-grouper-agent/actions/workflows/claude-agent.yml/badge.svg)](https://github.com/meejain/url-pattern-grouper-agent/actions/workflows/claude-agent.yml)

An AI-powered tool that analyzes URLs and groups them based on common patterns. It also detects locales and maintains proper sorting.

## 🚀 Quick Run

Click the button below to run the URL Pattern Grouper:

[![Run Agentic AI](https://img.shields.io/badge/🤖_Run-Agentic_AI_Analysis-purple?style=for-the-badge&logoColor=white&labelColor=black)](https://github.com/meejain/url-pattern-grouper-agent/actions/workflows/claude-agent.yml)

## Features

- Groups URLs with similar path patterns (5+ matches)
- Detects language/locale codes (e.g., /es/, /ko.html)
- Maintains proper group sorting (Group 1, 2, 3...)
- Alphabetically sorts URLs within groups
- Exports results to Excel with clear formatting

## Output

The tool generates an Excel file with:
1. URL: The complete URL
2. Group: Pattern-based group (Group 1, 2, etc.)
3. Locale: Detected language code (defaults to "en") 