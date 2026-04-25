PS: Context-Disconnected Workflows & Friction.

The Context Gap: Current AI assistants live in isolated browser tabs. To get AI to help with an active task, a user must manually screenshot, copy-paste, switch apps, and write a heavy prompt. The AI is blind to the user's active OS environment.

The Interface Bottleneck: Navigating complex OS tasks or structuring raw ideas requires heavy manual UI interaction. Purely physical gesture controls (like Leap Motion) failed because they tried to replace the mouse, causing "Gorilla Arm" fatigue without adding intelligence.

The Crux: There is no frictionless bridge that combines what the user is looking at, what the user wants, and agentic execution in a single, fluid motion without breaking their workflow.

2. The Exact Solution (The "What" & "How")
The Pitch: We built a Multimodal Spatial Intent Engine—a lightweight, transparent OS overlay that fuses physical gestures, screen context, and voice commands to execute complex workflows via Gemini.

How It Actually Works (The Architecture):

The Dual-Trigger System (Zero Friction):

The Wow Factor: The user performs a physical "Pinch-and-Hold" macro-gesture (tracked locally via MediaPipe) while pointing at an area of interest on their screen.

The Power User Net: A global hotkey (Ctrl + Shift + Space) is available for high-speed users who don't want to lift their hands off the keyboard.

The Multimodal Capture (The Senses):

Upon trigger, the system instantly captures a high-resolution screenshot (what the user is looking at), records a short voice command (the intent), and captures a webcam frame.

The Gemini Orchestrator (The Brain):

The payload is sent to a decoupled local FastAPI microservice.

Gemini 1.5 Flash processes the screen context + voice command. Instead of just returning text, it uses Structured Outputs (JSON) and Function Calling to determine the exact system-level action required.

The Execution (The Result):

The AI agent executes the task (e.g., extracting data, saving a file, summarizing a spreadsheet) and projects the result directly onto a transparent, click-through desktop UI layer, meaning the user never had to leave their original application.