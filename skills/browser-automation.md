# Browser Automation (Playwright MCP)

Use this skill when a task requires controlling a real web browser: navigating pages, clicking
buttons, filling forms, taking screenshots, or scraping data from websites.

## Tool: playwright MCP server

The Playwright MCP controls a Chromium browser directly. No separate browser install needed
after initial setup.

## Core tools

### Navigation
```
browser_navigate(url)                    — navigate to a URL
browser_go_back() / browser_go_forward() — browser history
browser_reload()                         — refresh the page
browser_wait_for(selector, timeout)      — wait for element to appear
```

### Interaction
```
browser_click(selector)                  — click an element
browser_fill(selector, value)            — type into an input field
browser_select(selector, value)          — choose from a dropdown
browser_hover(selector)                  — hover over element
browser_press_key(key)                   — press a keyboard key
browser_drag(sourceSelector, targetSelector)
```

### Reading page content
```
browser_snapshot()                       — get accessibility tree of current page
browser_get_text(selector)               — extract text from element
browser_evaluate(jsCode)                 — run JavaScript on the page
```

### Screenshots and downloads
```
browser_screenshot()                     — capture screenshot (returns base64 image)
browser_pdf()                            — save page as PDF
browser_get_url()                        — get current URL
browser_get_title()                      — get page title
```

## Typical workflow

1. `browser_navigate(url)` — go to the page
2. `browser_snapshot()` — inspect the DOM to find element selectors
3. `browser_click` / `browser_fill` — interact with the page
4. `browser_screenshot()` — verify the state
5. Extract or download the target data

## When to use

- "Go to [URL] and download the report"
- "Navigate to the SharePoint page and get the latest file"
- "Fill in the form at [URL] with these details"
- "Scrape the table from [URL]"
- "Take a screenshot of [URL]"
- "Log into [site] and check my dashboard"
- Any task requiring clicking, filling, or reading a live webpage

## CSS selector tips

- ID: `#element-id`
- Class: `.class-name`
- Text: `text="button text"` (Playwright syntax)
- Aria: `[aria-label="Submit"]`
- When unsure: run `browser_snapshot()` first to inspect the DOM

## Safety rules

- Always `browser_snapshot()` before clicking to confirm the correct element
- Never enter credentials unless the user explicitly provides them
- Confirm with the user before submitting forms that take irreversible action
- Close the browser when done: `browser_close()`
