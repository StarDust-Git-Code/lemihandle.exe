# Prompt for Claude Opus 4.7

**Instructions:** Copy the text below the line and paste it directly into your chat with Claude Opus 4.7.

---

**Role:** You are a world-class Frontend Engineer and UI/UX Designer specializing in React, Tailwind CSS, and Framer Motion. 

**Task:** Build a stunning, modern, single-page product showcase website for a new open-source tool called **"Lemihandle"**.

**Project Context:**
Lemihandle is a "Spatial Intent Engine". It is an invisible layer that sits on your computer desktop. It watches your hands and face through your webcam, listens to your voice, and uses Google's multimodal "Gemini 2.5 Flash Lite" AI to instantly execute your intentions based on what is currently on your screen. 
- You pinch your fingers to trigger it.
- You open your palm to push-to-talk.
- You nod your head to confirm actions. 
- The architecture consists of a decoupled PyQt5/MediaPipe frontend overlay and a FastAPI backend brain.

**Tech Stack Requirements:**
- React (Functional components & Hooks)
- Tailwind CSS (for all styling)
- Framer Motion (for smooth scroll animations and micro-interactions)
- Lucide React (for iconography)

**Design Aesthetic:**
- **Theme:** Ultra-modern Dark Mode / Cyberpunk.
- **Colors:** Deep blacks/dark grays for the background. Neon accents (Electric Blue, Purple, and subtle Cyan glows).
- **Style:** Heavy use of **Glassmorphism** (translucent frosted glass cards with thin, semi-transparent borders and subtle drop shadows).
- **Typography:** Clean, sans-serif (e.g., Inter or Roboto) with high contrast for headings.

**Required Page Sections:**

1. **Hero Section:**
   - A massive, high-impact headline: "Your Computer. Controlled by Thought, Gesture, and Voice."
   - A subheadline: "Meet Lemihandle—the invisible, AI-powered spatial intent engine that lives on your desktop. No clicking. No typing. Just point, speak, and command."
   - Two Buttons: "View on GitHub" (Primary, glowing) and "Read the Docs" (Secondary, glassmorphic).
   - Place a placeholder for the hero image (`/assets/hero.png`).

2. **The Magic (Features Grid):**
   - A 3-column grid of glassmorphic cards using Lucide icons.
   - Card 1: "Spatial Gestures" (Pinch to capture, fist to dismiss, nod to confirm).
   - Card 2: "Instant Voice" (Push-to-talk microphone triggered by an open palm).
   - Card 3: "Gemini Brain" (Powered by Gemini 2.5 Flash Lite for multimodal reasoning).

3. **How It Works (Step-by-Step):**
   - An alternating zig-zag layout (Text on left, placeholder image/icon on right, then swapped).
   - Step 1: **Trigger** (Pinch your fingers).
   - Step 2: **Command** (Speak your intent).
   - Step 3: **Execute** (The AI executes tools on your PC and renders a floating glass UI).

4. **Architecture for Developers:**
   - A dark, sleek section explaining the architecture. 
   - Show a visual breakdown of the two decoupled microservices: 
     - **Frontend:** PyQt5 transparent overlay + MediaPipe tracking thread.
     - **Backend:** FastAPI + Gemini API + local system tools.
   - Include a mock terminal window component showing a `git clone` and `docker-compose up` command.

5. **Footer:**
   - Simple links to GitHub, MIT License, and a bold final Call-to-Action.

**Deliverable:**
Please provide the complete, production-ready React code (you can output it as a single cohesive file or distinct components). Ensure that Framer Motion is heavily utilized for fade-ins, slide-ups, and hover effects on the glassmorphic cards to make the website feel "alive".
