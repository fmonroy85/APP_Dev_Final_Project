---
name: workspace-instructions
description: "Bootstrap workspace instructions for APP_Dev_Final_Project medical concierge app"
---

# APP_Dev_Final_Project workspace instructions

- This repo appears to be a new medical concierge app final project with only `README.md` present.
- Use this file for shared AI guidance until project structure expands.

## Primary goals

- Support project setup and planning when there is currently no source code.
- Help generate architecture, file scaffolding, and development tasks for a small healthcare concierge application.
- Avoid assuming any existing framework; ask the user for target platforms and technologies before scaffolding.

## What to do first

- Review `README.md` for the project name and purpose.
- Ask the user to describe intended features, target platform (web/mobile/backend), and preferred tech stack.
- If code is added, also look for package manifests, build scripts, or directories to infer frameworks.

## How I should help

- Keep suggestions aligned with a medical concierge app: patient scheduling, provider search, booking, messaging, and care coordination.
- Prefer incremental scaffolding: define data models, API shape, and UI structure before generating full modules.
- When given files, preserve existing docs and avoid replacing any README or project summary content.
- If the repo has no instructions or automation, recommend adding `CONTRIBUTING.md`, `ARCHITECTURE.md`, or build/test scripts.

## Known constraints

- No build/test commands are available in the current workspace.
- There is no existing source code or folder structure to infer conventions from.
- Do not invent an existing codebase; instead, guide the user to provide more details before generating large scaffolding.

## Example prompts

- "Help me plan the backend and frontend architecture for this medical concierge app."
- "Create a starter file structure for a medical concierge app using React and Node.js."
- "Suggest user stories and database models for a medical concierge service."

This simple instruction file is enough for now.
