# Memoir - Comprehensive UI/UX Redesign Specification
## Benchmarked against Google NotebookLM

---

## 1. Design Philosophy & Principles

### 1.1 Problem Statement
The current Memoir UI suffers from three critical issues that make it feel AI-generated rather than professionally crafted:
1. **Emoji overload**: 42+ emoji instances used as icons throughout the app (navigation, section headers, avatars, badges, empty states, error states)
2. **Glassmorphism fatigue**: backdrop-filter blur on every card creates visual noise and harms readability
3. **Aggressive dark theme**: hardcoded deep-black backgrounds (#0a0a0f) with purple gradient accents create a "hacker tool" aesthetic rather than a professional knowledge management tool

### 1.2 Design Principles (from NotebookLM Benchmark)

| Principle | Current Memoir | Target (NotebookLM-inspired) |
|-----------|---------------|------------------------------|
| Surface strategy | Single deep-black bg (#0a0a0f) | Layered neutral surfaces with subtle depth |
| Color accent | Purple gradient (#6366f1 -> #8b5cf6) | Single muted blue accent, used sparingly |
| Card treatment | Glassmorphism with blur | Flat with subtle border (dark) or tinted bg (light) |
| Icon system | Emoji characters | SVG icon library (Lucide React) |
| Typography weight | Mixed, often heavy | Predominantly regular (400) for headings, medium (500) for labels |
| Information density | Medium | Medium-high, clean spacing |
| Visual hierarchy | Competing elements (glow, gradients, emojis) | Clear typographic hierarchy with restrained color |

### 1.3 Core Design Decisions & Rationale

**Why remove emojis?** Emojis render inconsistently across operating systems (Windows vs Mac vs Linux), have no hover/active states, cannot be styled with CSS (color, size adjustments are limited), and are the single biggest signal of an AI-generated UI. Professional apps universally use SVG icon systems.

**Why remove glassmorphism?** Backdrop-filter blur is computationally expensive (causes frame drops on lower-end devices), creates inconsistent visual density depending on what sits behind the card, and has become strongly associated with AI-generated design templates since 2023.

**Why add light mode?** NotebookLM defaults to system preference (prefers-color-scheme). Most professional knowledge tools (Notion, Obsidian, Google Docs) default to light mode. A light-first approach with dark mode support signals maturity.

---

## 2. Color System

### 2.1 Light Mode Palette (Default)

```css
:root {
  /* ---- Surfaces ---- */
  --bg-primary: #ffffff;              /* Page background */
  --bg-secondary: #f7f8fa;            /* Sidebar, secondary panels */
  --bg-tertiary: #f0f1f4;             /* Elevated cards, input backgrounds */
  --bg-card: #ffffff;                 /* Card background */
  --bg-card-hover: #f7f8fa;           /* Card hover state */
  --bg-surface-raised: #eceef2;       /* Raised surfaces, chips, badges */

  /* ---- Text ---- */
  --text-primary: #1f1f1f;            /* Headings, primary content */
  --text-secondary: #535559;           /* Body text, descriptions */
  --text-muted: #80838a;              /* Placeholders, timestamps, meta */
  --text-inverse: #ffffff;            /* Text on dark/accent backgrounds */

  /* ---- Accent (Blue) ---- */
  --accent-primary: #1a73e8;          /* Links, active states, primary CTA */
  --accent-primary-hover: #1557b0;    /* Hover state for accent */
  --accent-bg: rgba(26, 115, 232, 0.08); /* Light accent background tint */
  --accent-bg-hover: rgba(26, 115, 232, 0.12);

  /* ---- Borders ---- */
  --border-primary: #dadce0;          /* Default border */
  --border-secondary: #e8eaed;        /* Subtle border */
  --border-focus: #1a73e8;            /* Focus ring border */

  /* ---- Semantic ---- */
  --color-success: #188038;
  --color-success-bg: #e6f4ea;
  --color-warning: #e37400;
  --color-warning-bg: #fef7e0;
  --color-error: #d93025;
  --color-error-bg: #fce8e6;
  --color-info: #1a73e8;
  --color-info-bg: #e8f0fe;

  /* ---- Shadows ---- */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.10);
  --shadow-md: 0 1px 3px rgba(0, 0, 0, 0.08), 0 4px 8px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.06), 0 10px 24px rgba(0, 0, 0, 0.10);
  --shadow-focus: 0 0 0 2px rgba(26, 115, 232, 0.20);
}
```

### 2.2 Dark Mode Palette

```css
@media (prefers-color-scheme: dark) {
  :root {
    /* ---- Surfaces ---- */
    --bg-primary: #1a1a1a;              /* Page background */
    --bg-secondary: #212121;            /* Sidebar, secondary panels */
    --bg-tertiary: #2c2c2c;             /* Elevated cards, input backgrounds */
    --bg-card: #2c2c2c;                /* Card background */
    --bg-card-hover: #333333;           /* Card hover state */
    --bg-surface-raised: #383838;       /* Raised surfaces, chips, badges */

    /* ---- Text ---- */
    --text-primary: #e8eaed;            /* Headings, primary content */
    --text-secondary: #bdc1c6;          /* Body text, descriptions */
    --text-muted: #9aa0a6;             /* Placeholders, timestamps, meta */
    --text-inverse: #1a1a1a;           /* Text on light/accent backgrounds */

    /* ---- Accent (Blue) ---- */
    --accent-primary: #8ab4f8;          /* Links, active states */
    --accent-primary-hover: #aecbfa;    /* Hover state for accent */
    --accent-bg: rgba(138, 180, 248, 0.10);
    --accent-bg-hover: rgba(138, 180, 248, 0.16);

    /* ---- Borders ---- */
    --border-primary: #3c4043;          /* Default border */
    --border-secondary: #303134;        /* Subtle border */
    --border-focus: #8ab4f8;

    /* ---- Semantic ---- */
    --color-success: #81c995;
    --color-success-bg: rgba(129, 201, 149, 0.12);
    --color-warning: #fdd663;
    --color-warning-bg: rgba(253, 214, 99, 0.12);
    --color-error: #f28b82;
    --color-error-bg: rgba(242, 139, 130, 0.12);
    --color-info: #8ab4f8;
    --color-info-bg: rgba(138, 180, 248, 0.12);

    /* ---- Shadows ---- */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.30);
    --shadow-md: 0 1px 3px rgba(0, 0, 0, 0.30), 0 4px 8px rgba(0, 0, 0, 0.20);
    --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.20), 0 10px 24px rgba(0, 0, 0, 0.30);
    --shadow-focus: 0 0 0 2px rgba(138, 180, 248, 0.30);
  }
}
```

### 2.3 Manual Theme Toggle (data-attribute approach)

For users who want to override system preference, use `data-theme="light"` or `data-theme="dark"` on `<html>`. CSS structure:

```
:root { /* light mode defaults */ }
@media (prefers-color-scheme: dark) { :root { /* dark overrides */ } }
[data-theme="light"] { /* force light */ }
[data-theme="dark"] { /* force dark */ }
```

### 2.4 Colors to REMOVE

| Current Variable | Value | Action |
|-----------------|-------|--------|
| --accent-gradient | linear-gradient(135deg, #6366f1...) | DELETE entirely. No gradients on surfaces. |
| --glass-bg | rgba(255,255,255,0.03) | DELETE. No glassmorphism. |
| --shadow-glow | 0 0 30px rgba(99,102,241,0.15) | DELETE. No colored glow effects. |
| --bg-primary | #0a0a0f | REPLACE with layered system above |
| --bg-secondary | #12121a | REPLACE |
| --bg-tertiary | #1a1a25 | REPLACE |
| --bg-card | rgba(26,26,37,0.8) | REPLACE. No alpha transparency on cards. |

---

## 3. Typography System

### 3.1 Font Stack

```css
:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}
```

**Rationale**: Keep Inter as the primary font (already in use). Add 'Noto Sans KR' for Korean text rendering, matching NotebookLM's approach.

### 3.2 Type Scale

| Token | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| --text-display | 28px | 400 | 36px | -0.02em | Page titles (Dashboard, Settings) |
| --text-headline | 22px | 400 | 28px | -0.01em | Section headers |
| --text-title | 16px | 500 | 24px | normal | Card titles, nav labels |
| --text-body | 14px | 400 | 22px | normal | Body text, descriptions |
| --text-body-sm | 13px | 400 | 20px | normal | Secondary body text |
| --text-label | 12px | 500 | 16px | 0.02em | Badges, chips, timestamps |
| --text-caption | 11px | 400 | 16px | 0.03em | Meta text, footnotes |

**Key change from current**: NotebookLM uses **weight 400 for headings**, not 600-700. This is a deliberate Material Design 3 pattern -- headings are distinguished by SIZE, not weight. Weight 500 is reserved for interactive labels (buttons, tabs, nav items).

### 3.3 CSS Implementation

```css
:root {
  /* Font sizes */
  --fs-display: 1.75rem;      /* 28px */
  --fs-headline: 1.375rem;    /* 22px */
  --fs-title: 1rem;            /* 16px */
  --fs-body: 0.875rem;         /* 14px */
  --fs-body-sm: 0.8125rem;     /* 13px */
  --fs-label: 0.75rem;         /* 12px */
  --fs-caption: 0.6875rem;     /* 11px */

  /* Line heights */
  --lh-tight: 1.25;
  --lh-normal: 1.5;
  --lh-relaxed: 1.625;
}
```

---

## 4. Spacing System

### 4.1 Base Scale (4px grid)

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-5: 1.25rem;   /* 20px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
  --space-10: 2.5rem;   /* 40px */
  --space-12: 3rem;     /* 48px */
  --space-16: 4rem;     /* 64px */
}
```

### 4.2 Border Radius

```css
:root {
  --radius-sm: 4px;     /* Small chips, inline elements */
  --radius-md: 8px;     /* Buttons, inputs, small cards */
  --radius-lg: 12px;    /* Cards, modals (NotebookLM uses 12px) */
  --radius-xl: 16px;    /* Large panels, feature cards */
  --radius-full: 9999px; /* Pill buttons, avatars */
}
```

**Key change**: NotebookLM consistently uses 12px border-radius on cards. Current Memoir uses --radius-lg: 0.75rem (12px), which is coincidentally correct. Buttons should use 8px (or 100px/9999px for pill-shaped CTAs like "New Chat").

### 4.3 Transitions

```css
:root {
  --transition-fast: 100ms ease-out;
  --transition-normal: 200ms ease-out;
  --transition-slow: 300ms ease-out;
}
```

---

## 5. Icon System: Complete Emoji-to-Lucide Mapping

### 5.1 Navigation Icons

| Location | Current Emoji | Lucide Icon Name | Rationale |
|----------|--------------|-----------------|-----------|
| Sidebar: Chat | `💬` | `MessageSquare` | Standard messaging icon |
| Sidebar: Memories | `🧠` | `BookOpen` | Knowledge/source icon (NotebookLM uses document icons for sources) |
| Sidebar: Journal | `📝` | `PenLine` | Writing/editing icon |
| Sidebar: Search | `🔍` | `Search` | Universal search icon |
| Sidebar: Graph | `🕸️` | `Network` | Network/connection graph |
| Sidebar: Dashboard | `📊` | `LayoutDashboard` | Dashboard layout icon |
| Sidebar: Timeline | `📅` | `Clock` | Temporal/chronological icon |
| Sidebar: Settings | `⚙️` | `Settings` | Universal settings gear |

### 5.2 Logo & Auth

| Location | Current | Replacement | Notes |
|----------|---------|-------------|-------|
| Sidebar Logo | `📚` emoji | `memoir.png` brand image (28x28) | Use the existing brand illustration as a small icon |
| Auth Page Logo | `📚` emoji | `memoir.png` brand image (64x64) | Larger version for auth splash |

### 5.3 Dashboard Icons

| Location | Current Emoji | Lucide Icon Name |
|----------|--------------|-----------------|
| Page title "Dashboard" | `📊` | REMOVE emoji. Plain text heading only. |
| "Today's Overview" section | `🌅` | REMOVE emoji. Plain text heading only. |
| "AI Recommended Questions" | `🤔` | `Sparkles` (only if icon needed) or REMOVE |
| "Today's Saved Content" | `📝` | REMOVE emoji. Plain text heading only. |
| "Recent 7-Day Activity" | `📈` | REMOVE emoji. Plain text heading only. |
| "Source Type Distribution" | `📁` | REMOVE emoji. Plain text heading only. |
| "Popular Tags" | `🏷️` | REMOVE emoji. Plain text heading only. |
| Stat card: Total memories | `📚` | `Database` |
| Stat card: This week | `📅` | `CalendarDays` |
| Stat card: This month | `📆` | `Calendar` |
| Stat card: Most active day | `🔥` | `TrendingUp` |
| Error state | `⚠️` | `AlertCircle` |

**Key principle from NotebookLM**: Section headings do NOT have icons. Only individual items (source type badges, stat cards) use icons. This is a critical difference -- the current Memoir puts an emoji before EVERY heading, which is the most obvious AI-generated pattern.

### 5.4 Chat Icons

| Location | Current | Lucide Icon Name |
|----------|---------|-----------------|
| User avatar | `👤` | `User` (or use actual user avatar image if available) |
| Assistant avatar | `🧠` | `Bot` or custom SVG "M" monogram |
| Empty state | `🤔` | `MessageSquareText` |
| Send button | `→` (text) | `ArrowUp` (NotebookLM uses a circled arrow) |
| Mode: Default | `💬` | `MessageSquare` |
| Mode: Insight | `💡` | `Lightbulb` |
| Mode: Counter | `⚖️` | `Scale` |
| Mode: Summary | `📋` | `ClipboardList` |
| Mode: Evening | `🌙` | `Moon` |
| Mode dropdown arrow | `▼` (text) | `ChevronDown` |

### 5.5 Memory View Icons

| Location | Current Emoji | Lucide Icon Name |
|----------|--------------|-----------------|
| Source type: WEB | `🌐` | `Globe` |
| Source type: PDF | `📄` | `FileText` |
| Source type: NOTE | `📝` | `StickyNote` |
| Source type: fallback | `📋` | `File` |
| Empty state | `📦` | `FolderOpen` |
| Modal tab: Web URL | `🌐` | `Globe` |
| Modal tab: Note | `📝` | `StickyNote` |
| Modal tab: PDF | `📄` | `FileText` |
| PDF upload label | `📄` | `Upload` |

### 5.6 Search View Icons

| Location | Current Emoji | Lucide Icon Name |
|----------|--------------|-----------------|
| Page title | `🔍` | REMOVE emoji from heading |
| Filter button | `⚙️` | `SlidersHorizontal` |
| Empty result | `🤔` | `SearchX` |
| Source badge | `getSourceIcon()` emoji | Same Lucide icons as Memory View |

### 5.7 Timeline View Icons

| Location | Current Emoji | Lucide Icon Name |
|----------|--------------|-----------------|
| Page title | `📅` | REMOVE emoji from heading |
| Empty state | `📅` | `CalendarX2` |
| Error state | `⚠️` | `AlertCircle` |

### 5.8 Journal View Icons

| Location | Current Emoji | Lucide Icon Name |
|----------|--------------|-----------------|
| Related Memories header | `📚` | `BookOpen` |

### 5.9 Other

| Location | Current | Lucide Icon Name |
|----------|---------|-----------------|
| Logout button | `🚪` | `LogOut` |
| Session toggle arrow | `▾` / `▸` | `ChevronDown` / `ChevronRight` |
| Close buttons | `×` (text) | `X` |

### 5.10 Icon Sizing Convention

| Context | Size | Stroke Width |
|---------|------|-------------|
| Navigation sidebar | 20px | 1.75px |
| Inline with text (badges) | 16px | 1.75px |
| Section/card icons | 20px | 1.75px |
| Empty state illustrations | 48px | 1.5px |
| Button icons | 16px | 2px |
| Chat avatars | 24px | 1.75px |

### 5.11 getSourceIcon() Utility Refactor

The `getSourceIcon()` function in `frontend/src/utils/format.ts` currently returns emoji strings. It must be refactored to return Lucide component names (or JSX elements) instead:

```
Current: getSourceIcon('WEB') => '🌐'
Target:  getSourceIcon('WEB') => <Globe size={16} />
```

---

## 6. Component-by-Component Specifications

### 6.1 Sidebar

**Current problems**: Emoji icons, purple accent active state, gradient CTA button, emoji logout button.

**Target design (inspired by NotebookLM's clean navigation)**:

```
Layout:
+-----------------------------------+
| [memoir.png 24px] Memoir          |  <- Logo area, 56px height
+-----------------------------------+
| + New Chat (pill button)          |  <- Primary CTA
+-----------------------------------+
|  [icon] Chat                      |  <- Nav items, 36px height each
|  [icon] Memories                  |
|  [icon] Journal                   |
|  [icon] Search                    |
|  [icon] Graph                     |
|  [icon] Dashboard                 |
|  [icon] Timeline                  |
+-----------------------------------+
|  RECENT CHATS (section label)     |  <- Collapsed section
|    Session title 1                |
|    Session title 2                |
+-----------------------------------+
|  [icon] Settings                  |  <- Bottom-pinned
+-----------------------------------+
|  [avatar] User Name              |  <- User section
|           email@test.com [logout] |
+-----------------------------------+
```

**Specs:**
- Width: 240px (reduced from 250px)
- Background: var(--bg-secondary)
- Border-right: 1px solid var(--border-secondary)
- Nav item height: 36px
- Nav item padding: 8px 12px
- Nav item icon size: 20px
- Nav item font: 14px / 500
- Nav item default color: var(--text-secondary)
- Nav item hover: background var(--bg-tertiary), color var(--text-primary)
- Nav item active: background var(--accent-bg), color var(--accent-primary), font-weight 500
- NO purple background tint on active. Use the accent-bg (subtle blue tint).
- "New Chat" button: pill shape (border-radius: 9999px), full width, 36px height
  - Light mode: bg var(--text-primary) (#1f1f1f), color white
  - Dark mode: bg var(--text-primary) (#e8eaed), color var(--text-inverse)
- Session section label: 11px, uppercase, letter-spacing 0.05em, weight 500, color var(--text-muted)
- Logout icon: `LogOut` Lucide icon, 16px, color var(--text-muted), hover color var(--color-error)

### 6.2 AuthView (Login Page)

**Current problems**: Emoji logo, glassmorphism card, dark-only.

**Target design:**

```
Layout (centered vertically and horizontally):
+---------------------------------------+
|                                       |
|        [memoir.png 64px]              |
|           Memoir                      |
|    Your personal knowledge partner    |
|                                       |
|  +-------------------------------+   |
|  | [G icon] Continue with Google |   |  <- 48px height buttons
|  +-------------------------------+   |
|  | [K icon] Continue with Kakao  |   |
|  +-------------------------------+   |
|                                       |
|  [error message area]                 |
+---------------------------------------+
```

**Specs:**
- Page background: var(--bg-primary)
- Card: max-width 400px, no border, no shadow, no glassmorphism
- Logo image: 64x64px, margin-bottom 16px
- Title: 28px / 400 weight
- Subtitle: 14px / 400, color var(--text-secondary)
- OAuth buttons: full width, height 48px, border-radius 8px, border 1px solid var(--border-primary)
  - Background: var(--bg-primary) (transparent feel)
  - Hover: var(--bg-tertiary)
  - Font: 14px / 500
  - Icon: 18px, left-aligned with 12px gap
  - Google button: keep existing multi-color SVG
  - Kakao button: Kakao yellow background (#FEE500) with dark text (#3c1e1e)
- Error message: color var(--color-error), font-size 13px, margin-top 16px

### 6.3 DashboardView

**Current problems**: Emoji in every heading, glass-card on every section, stat cards with emoji icons.

**Target design:**

**Specs:**
- Page padding: 32px (desktop), 16px (mobile)
- Page title: "Dashboard" -- plain text, 28px / 400, no emoji
- Subtitle: 14px, color var(--text-secondary), margin-bottom 24px
- Section headings: 18px / 500, no emoji prefix, margin-bottom 16px

**Stat cards grid:**
- 4 columns on desktop, 2 on tablet, 1 on mobile
- Card: border-radius 12px, padding 20px
  - Light: bg var(--bg-card), border 1px solid var(--border-secondary)
  - Dark: bg var(--bg-card), border 1px solid var(--border-primary)
- Icon: 20px Lucide icon in a 36px circle with var(--accent-bg) background
- Stat value: 28px / 600
- Stat label: 12px / 500, color var(--text-muted), uppercase

**Activity chart:**
- Card container with same treatment as stat cards
- Bar color: var(--accent-primary) at 60% opacity, hover at 100%
- Axis labels: 11px, color var(--text-muted)

**Source distribution / Tag cloud:**
- Same card container
- Progress bars: 4px height, border-radius 2px, bg var(--accent-primary)
- Tags: inline chips with var(--bg-surface-raised) background, border-radius 9999px, padding 4px 12px, font 12px / 500

### 6.4 ChatView

**Current problems**: Emoji avatars (user=👤, assistant=🧠), emoji mode icons, emoji empty state.

**Target design (inspired by NotebookLM's chat):**

```
Layout:
+------------------------------------------+
| Socrates                    [mode dropdown]|  <- Header
| Your thinking partner                      |
+------------------------------------------+
|                                            |
|  [user avatar] User message               |  <- Messages area
|                                            |
|  [M avatar]   Assistant response          |
|               with markdown rendering      |
|                                            |
+------------------------------------------+
| [textarea input]              [send btn]  |  <- Input area
+------------------------------------------+
```

**Specs:**
- Header: padding 16px 24px, border-bottom 1px solid var(--border-secondary)
- Title "Socrates": 22px / 400
- Subtitle: 13px, color var(--text-muted)

**Message bubbles:**
- User message: right-aligned is NOT the target. NotebookLM uses left-aligned for both. Follow the same pattern.
- User avatar: 32px circle, either user's actual avatar image or initials in a colored circle (bg var(--accent-primary), color white)
- Assistant avatar: 32px circle with a stylized "M" or the Bot icon, bg var(--bg-surface-raised)
- Message text: 14px / 1.625 line-height
- Message padding: 0 (no bubble background for text; only avatar + text layout)
- Spacing between messages: 24px

**Mode selector:**
- Dropdown button: border-radius 8px, border 1px solid var(--border-primary), padding 8px 12px
- Icon: 16px Lucide icon (not emoji)
- Dropdown: bg var(--bg-card), border 1px solid var(--border-primary), shadow var(--shadow-lg), border-radius 12px
- Active mode: bg var(--accent-bg), color var(--accent-primary)

**Input area:**
- Container: border-top 1px solid var(--border-secondary), padding 16px 24px
- Textarea: bg var(--bg-tertiary), border-radius 24px (pill), padding 12px 48px 12px 16px, min-height 44px
  - Focus: border-color var(--border-focus), shadow var(--shadow-focus)
- Send button: 36px circle, positioned inside textarea (right side)
  - Default: bg var(--bg-surface-raised), color var(--text-muted)
  - Active (has input): bg var(--text-primary), color var(--bg-primary)
  - Icon: ArrowUp, 18px

**Empty state:**
- Centered vertically
- Icon: MessageSquareText, 48px, color var(--text-muted), opacity 0.5
- Heading: 18px / 400, color var(--text-primary)
- Description: 14px, color var(--text-secondary)

### 6.5 MemoryView (Sources)

**Current problems**: Emoji source badges, glassmorphism cards, emoji in modal tabs.

**Target design (inspired by NotebookLM's source list):**

**Specs:**
- Page header: "Memories" 28px / 400, subtitle 14px var(--text-secondary)
- "+ Add" button: same pill style as "New Chat" or outlined with border

**Memory cards grid:**
- 3 columns desktop, 2 tablet, 1 mobile
- Card: border-radius 12px, padding 16px, border 1px solid var(--border-secondary)
- Source type badge: top-left corner
  - Icon: 16px Lucide icon (Globe/FileText/StickyNote)
  - Container: 28px pill shape, bg var(--bg-surface-raised), font 11px / 500
  - Text label next to icon (e.g., "WEB", "PDF", "NOTE")
- Title: 16px / 500, color var(--text-primary), max 2 lines with ellipsis
- Summary: 13px / 400, color var(--text-secondary), max 3 lines
- Date: 11px, color var(--text-muted)

**Add Memory Modal:**
- Overlay: rgba(0,0,0,0.5) -- NOT glass blur
- Modal: max-width 480px, border-radius 16px, bg var(--bg-card), padding 24px
- Tabs: text-based segmented control (not emoji tabs)
  - Active: color var(--accent-primary), border-bottom 2px solid var(--accent-primary)
  - Inactive: color var(--text-secondary)
  - NO emoji before tab labels
- Input: standard input styling (see Section 8)
- Buttons: "Cancel" = ghost/secondary, "Save" = filled primary

### 6.6 SearchView

**Target design:**
- Page title: "Semantic Search" -- no emoji, 28px / 400
- Search bar: prominent, full width
  - Input: bg var(--bg-tertiary), border-radius 24px (pill), height 48px, padding 0 48px 0 16px
  - Search icon: 20px, inside left side, color var(--text-muted)
  - Filter button: icon-only (SlidersHorizontal), right side of search bar, no emoji
- Filter panel: slides down below search bar, bg var(--bg-tertiary), border-radius 12px
  - Select dropdowns: standard styling
  - "Clear filters" link: text button, color var(--accent-primary)
- Result cards: same card treatment as Memory cards
  - Similarity badge: pill shape, bg varies by level:
    - High (>=80%): bg var(--color-success-bg), color var(--color-success)
    - Medium (50-79%): bg var(--color-warning-bg), color var(--color-warning)
    - Low (<50%): bg var(--bg-surface-raised), color var(--text-muted)

### 6.7 JournalView

**No significant emoji issues** except Related Memories header. Specs:
- Related Memories header: "Related Memories" plain text with BookOpen icon (16px) inline, no emoji
- Editor header: clean button styling (no emoji)
- Session picker modal: same modal treatment as MemoryView modal

### 6.8 GraphView

**No emoji issues** (already uses SVG). Specs updates:
- Background color: must adapt to theme
  - Light: var(--bg-primary)
  - Dark: var(--bg-primary)
  - Currently hardcoded as `backgroundColor="#0a0a0f"` -- must use CSS variable
- Search bar: consistent with SearchView pill input
- Legend: bg var(--bg-card), border 1px solid var(--border-primary), border-radius 12px
- Info panel: same card treatment

### 6.9 TimelineView

**Current problems**: Emoji page title, emoji empty state.

**Specs:**
- Page title: "Timeline" -- no emoji, 28px / 400
- Timeline line: 2px wide, color var(--border-primary)
- Date marker: bg var(--bg-surface-raised), color var(--text-primary), border-radius 9999px, padding 4px 16px, font 13px / 500
- Timeline cards: same card treatment as Memory cards
- Tags: inline chips, same as Dashboard tag styling

### 6.10 SettingsView

**No emoji issues** (already cleaned). Specs updates:
- Remove `glass-card` class from all cards
- Apply standard card treatment (border, no blur, no alpha bg)
- Toggle switch: standard iOS-style toggle
  - Track: 44px x 24px, border-radius 12px
  - Off: bg var(--border-primary)
  - On: bg var(--accent-primary)
  - Thumb: 20px circle, white, shadow var(--shadow-sm)
- Status badges:
  - Connected: bg var(--color-success-bg), color var(--color-success)
  - Upcoming: bg var(--bg-surface-raised), color var(--text-muted)

---

## 7. Global Component Patterns

### 7.1 Cards (replacing .glass-card)

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);     /* 12px */
  padding: var(--space-5);             /* 20px */
  transition: border-color var(--transition-fast);
}

.card:hover {
  border-color: var(--border-primary);
}

/* NO backdrop-filter. NO rgba backgrounds. NO box-shadow by default. */
```

### 7.2 Buttons

**Primary (filled):**
```css
.btn-primary {
  background: var(--text-primary);     /* Black in light, near-white in dark */
  color: var(--bg-primary);            /* White in light, dark in dark */
  border: none;
  border-radius: var(--radius-md);     /* 8px */
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  height: 36px;
  transition: opacity var(--transition-fast);
}

.btn-primary:hover {
  opacity: 0.85;
}

/* NO gradient. NO glow shadow. NO translateY transform. */
```

**Secondary (outlined):**
```css
.btn-secondary {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 500;
  height: 36px;
}

.btn-secondary:hover {
  background: var(--bg-tertiary);
}
```

**Ghost (text only):**
```css
.btn-ghost {
  background: transparent;
  color: var(--accent-primary);
  border: none;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
}

.btn-ghost:hover {
  background: var(--accent-bg);
  border-radius: var(--radius-md);
}
```

**Pill CTA (e.g., New Chat, primary action):**
```css
.btn-pill {
  border-radius: var(--radius-full);   /* 9999px */
  /* Same as primary otherwise */
}
```

### 7.3 Inputs

```css
.input {
  width: 100%;
  padding: 10px 14px;
  font-size: 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-md);     /* 8px */
  color: var(--text-primary);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input:hover {
  border-color: var(--border-primary);
}

.input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: var(--shadow-focus);
}

.input::placeholder {
  color: var(--text-muted);
}

/* NO purple focus ring. Use blue. */
```

### 7.4 Modal / Dialog

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);     /* NOT glass blur */
  /* NO backdrop-filter */
}

.modal-content {
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 16px;
  padding: 24px;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
}
```

### 7.5 Tabs

```css
.tab {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  background: none;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}
```

### 7.6 Badges / Chips

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius-full);
  background: var(--bg-surface-raised);
  color: var(--text-secondary);
}

.badge-success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.badge-error {
  background: var(--color-error-bg);
  color: var(--color-error);
}
```

### 7.7 Empty / Error / Loading States

```css
/* Shared layout */
.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
  gap: 12px;
}

/* Icon: use Lucide icon, NOT emoji */
.state-icon {
  color: var(--text-muted);
  opacity: 0.4;
  margin-bottom: 8px;
  /* Size: 48px for empty/error, see component spec */
}

/* NO font-size: 3rem emoji. Use Lucide SVG at specific pixel sizes. */

.state-title {
  font-size: 18px;
  font-weight: 400;         /* NOT bold */
  color: var(--text-primary);
}

.state-description {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 320px;
}
```

### 7.8 Loading Spinner

```css
.spinner {
  width: 24px;
  height: 24px;
  border: 2.5px solid var(--border-primary);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* NO purple border-top-color. Use blue accent. */
```

### 7.9 Toast / Notification

```css
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
  box-shadow: var(--shadow-lg);
  z-index: 1000;
  animation: slideUp 200ms ease-out;
}

/* Light mode: dark toast (matches NotebookLM's snackbar) */
.toast { background: var(--text-primary); color: var(--bg-primary); }

/* Variants override with semantic colors only for icons/accents */
```

### 7.10 Scrollbar

```css
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: var(--radius-full);
  border: 2px solid var(--bg-primary);    /* Creates inset effect */
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
```

---

## 8. Interaction States

### 8.1 Focus States (Accessibility)

Every interactive element MUST have a visible focus indicator:

```css
/* Default focus for keyboard users */
:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}

/* Remove default outline for mouse users */
:focus:not(:focus-visible) {
  outline: none;
}

/* Input-specific focus (uses inset shadow instead of outline) */
input:focus-visible,
textarea:focus-visible,
select:focus-visible {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: var(--shadow-focus);
}
```

### 8.2 State Matrix

| Element | Default | Hover | Active/Pressed | Focus | Disabled |
|---------|---------|-------|----------------|-------|----------|
| btn-primary | bg: text-primary | opacity: 0.85 | opacity: 0.75 | outline ring | opacity: 0.4, cursor: not-allowed |
| btn-secondary | border: border-primary | bg: bg-tertiary | bg: border-primary (darker) | outline ring | opacity: 0.4, cursor: not-allowed |
| nav-item | color: text-secondary | bg: bg-tertiary | -- | bg: accent-bg | -- |
| nav-item.active | bg: accent-bg, color: accent | -- | -- | -- | -- |
| card | border: border-secondary | border: border-primary | -- | outline ring | opacity: 0.6 |
| input | border: border-secondary | border: border-primary | -- | shadow-focus | bg: bg-tertiary (darker), opacity: 0.6 |
| link | color: accent-primary | text-decoration: underline | color: accent-hover | outline ring | color: text-muted |
| tab | color: text-secondary | color: text-primary | -- | outline ring | opacity: 0.4 |
| tab.active | color: accent, border-bottom: accent | -- | -- | -- | -- |
| toggle OFF | bg: border-primary | opacity: 0.85 | -- | outline ring | opacity: 0.4 |
| toggle ON | bg: accent-primary | opacity: 0.85 | -- | outline ring | opacity: 0.4 |

---

## 9. Responsive Breakpoints

```css
/* Mobile first */
--bp-sm: 640px;    /* Small tablets */
--bp-md: 768px;    /* Tablets */
--bp-lg: 1024px;   /* Desktop */
--bp-xl: 1280px;   /* Large desktop */
```

### 9.1 Sidebar Behavior
- **>= 1024px**: Sidebar visible, 240px fixed width
- **768-1023px**: Sidebar collapsed to icon-only (56px width), expand on hover
- **< 768px**: Sidebar hidden, hamburger menu in header to toggle overlay

### 9.2 Grid Columns
- **Dashboard stat cards**: 4 / 2 / 1 columns at lg / md / sm
- **Memory cards**: 3 / 2 / 1 columns at lg / md / sm
- **Dashboard bottom row**: 2 / 1 columns at lg / sm

---

## 10. CSS Classes to DELETE

The following CSS classes and patterns must be completely removed:

| Class/Pattern | Reason |
|---------------|--------|
| `.glass-card` | Glassmorphism eliminated |
| `backdrop-filter: blur(...)` | No blur effects anywhere |
| `var(--accent-gradient)` | No gradient backgrounds |
| `var(--glass-bg)` | Transparent backgrounds eliminated |
| `var(--shadow-glow)` | No colored glow effects |
| `transform: translateY(-1px)` on hover | No "lift" effect on buttons |
| `.error-icon`, `.empty-icon` with `font-size: 3rem` | Emoji sizing eliminated |
| All `rgba(99, 102, 241, ...)` references | Purple accent replaced with blue |
| `background: #0a0a0f` (hardcoded in GraphView) | Must use CSS variable |

---

## 11. Microcopy Recommendations

| Element | Current Text | Recommended | Tone |
|---------|-------------|-------------|------|
| Auth subtitle | "지능형 인지 장부" | "나만의 지식 파트너" | Warm, personal |
| Chat empty heading | "무엇이 궁금하신가요?" | "무엇이 궁금하세요?" (slightly less formal) | Conversational |
| Chat input placeholder | "메시지를 입력하세요..." | "질문하거나 대화를 시작하세요" | Action-oriented |
| Memory empty heading | "아직 저장된 기억이 없습니다" | "아직 저장된 내용이 없습니다" | Neutral ("기억" is too metaphorical) |
| Memory empty sub | "웹 페이지나 메모를 추가해보세요" | Keep as-is | Clear |
| Search placeholder | "예: 마케팅 전략에 대해 읽었던 글..." | Keep as-is | Helpful example |
| Search empty heading | "관련 기억을 찾지 못했습니다" | "관련 내용을 찾지 못했습니다" | Consistent with "내용" terminology |
| Timeline empty | "아직 메모리가 없습니다" | "아직 저장된 내용이 없습니다" | Consistent |
| Dashboard subtitle | "나의 지식 활동 요약" | "활동 요약" | Concise |

---

## 12. Implementation Priority

### P0 - MVP (Must have for the redesign to feel complete)

1. **CSS Variable System**: Replace all :root variables with the light/dark dual system
2. **Remove all emojis**: Replace every emoji with Lucide React icons (42+ instances)
3. **Remove glassmorphism**: Delete `.glass-card`, remove all `backdrop-filter` usage
4. **Remove gradient accent**: Replace purple gradient with single blue accent
5. **Sidebar refactor**: New icon system, new active state, new CTA button
6. **Card refactor**: Replace glass-card with flat bordered cards
7. **AuthView cleanup**: Replace emoji logo with brand image

### P1 - Recommended (Polish the redesign)

1. **Typography weight adjustment**: Change heading weights from 600-700 to 400
2. **Input styling refresh**: Pill-shaped chat input, consistent input styling
3. **Empty/Error/Loading states**: SVG icons at proper sizes, professional copywriting
4. **Toast notifications**: Dark snackbar style matching NotebookLM
5. **Focus states**: Proper :focus-visible implementation for accessibility
6. **Modal styling**: Remove blur overlay, clean modal with proper shadows
7. **Responsive sidebar**: Collapsed icon-only mode for tablet, hamburger for mobile

### P2 - Future Iterations

1. **Manual theme toggle**: Add settings option for light/dark/system preference
2. **Animation refinement**: Subtle entrance animations for cards, page transitions
3. **Keyboard navigation**: Full tab-order implementation, escape key for modals
4. **Density option**: Compact vs comfortable spacing toggle
5. **Custom accent color**: User-selectable accent color in settings
6. **Skeleton loading states**: Replace spinners with content-shaped skeleton loaders

---

## 13. Summary of Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| Theme | Dark-only (#0a0a0f) | Light default + dark mode via prefers-color-scheme |
| Accent | Purple gradient (#6366f1-#8b5cf6) | Single muted blue (#1a73e8 light / #8ab4f8 dark) |
| Icons | 42+ emojis throughout | Lucide React SVG icons |
| Cards | Glassmorphism (blur + alpha bg) | Flat with 1px border, 12px radius |
| Headings | Weight 600-700 with emoji prefix | Weight 400, plain text only |
| Buttons | Gradient bg with glow shadow | Solid bg, no shadow, subtle opacity hover |
| Modals | Blur overlay | Semi-transparent dark overlay |
| Inputs | Purple focus ring | Blue focus ring with inset shadow |
| Scrollbar | Dark track | Transparent track with themed thumb |
| Logo | Emoji (book emoji) | Brand image (memoir.png) |
| Overall feel | "AI-generated dark dashboard" | "Professional knowledge tool" |
