# Dev B — Extended Independent Roadmap (Backend Enhancements)

While Dev A works on injecting the audio transcript into the JSON payload, **Developer B can continue hardening the backend orchestration** to make the AI "Brain" more powerful and resilient.

Here is the plan for what Developer B can build right now.

---

## 1. Advanced Local OS Actions (Expanding `tools.py`)

Right now, our local execution engine is limited to `save_output_to_file` and a simulated `open_application`. We can expand the capability of the AI to perform complex OS-level commands on Windows.

### Proposed Tools to Add:
1. **Clipboard Injection (`inject_to_clipboard`)**: 
   - *Action*: If the user says "copy this", the backend extracts the data and injects it directly into the Windows clipboard using `pyperclip`, ready for pasting.
2. **System Search / Web Search (`perform_search`)**:
   - *Action*: If the user asks a question requiring live info, the backend hits a search API (e.g., Tavily or DuckDuckGo) and feeds the results back into Gemini before answering.
3. **App Launching via Windows Shell (`launch_windows_app`)**:
   - *Action*: Using `os.system` or `subprocess`, the AI can actually spawn programs like "notepad", "calc", or specific URLs in the default browser.

---

## 2. Dynamic Memory Pruning (Context Optimization)

Our current `CHAT_HISTORY` memory simply truncates after 20 messages. This works, but it's brittle. If the user changes topics completely, the AI might hallucinate based on old context.

**Independent Implementation Plan:**
- Implement a `flush_context` command in the `SYSTEM_INSTRUCTION`.
- If the user says "start over" or "clear", the AI emits a `"function_triggered": "clear_memory"`.
- The backend intercepts this, wipes the `CHAT_HISTORY` array, and returns a fresh state.
- **Future:** Summarize past messages into a single "Memory Core" string instead of keeping raw transcripts to save massive token costs over long sessions.

---

## 3. Asynchronous Execution Workflows (Long-Running Tasks)

Currently, the `POST /process_intent` route is synchronous. The frontend blocks until Gemini replies. If we add tools that take a long time (like scraping a website), the HTTP request will timeout.

**Implementation Plan:**
- If the AI decides a task will take longer than 3 seconds, it replies with `"ui_directive": "display_notification"`, `"ai_output": "Working on it..."`, and a `"job_id"`.
- The backend immediately returns `200 OK` to the frontend, unblocking the UI.
- The backend spins up a background thread using `asyncio` or `BackgroundTasks` to complete the heavy lifting.
- *(Note: This requires modifying Dev A's network architecture to support polling or WebSockets in Phase 4).*

---

## Open Questions

> [!CAUTION]
> **Awaiting your approval to proceed.** Developer B is ready to execute all of the above without any interference from Developer A.
> 
> Please let me know:
> 1. Should we prioritize **Advanced OS Actions** so the AI feels more like a real desktop assistant?
> 2. Should we prioritize **Memory Pruning** to prevent token limits from crashing the app during extended demos?
> 3. Should we wait for Dev A's audio implementation before writing more backend code?
