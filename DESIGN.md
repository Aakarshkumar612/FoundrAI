# DESIGN.md — FoundrAI (Claude-inspired design system)

## Identity
Black base, warm terracotta accent (#D97757). Clean editorial layout for AI advisory.
Inspired by Claude (Anthropic). Best for: AI interfaces, data-dense dashboards, founder tools.

## Color Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| bg-base | #000000 | Page background |
| bg-surface | #0d0c0b | Cards, panels |
| bg-elevated | #161412 | Hover states, inputs |
| border | #1e1c1a | All borders |
| border-subtle | #2a2520 | Dividers |
| text-primary | #F5F0EB | Headings, body |
| text-secondary | #A89F95 | Secondary labels |
| text-muted | #6B6560 | Placeholders, meta |
| accent | #D97757 | Primary CTA, highlights |
| accent-hover | #C9623F | Button hover |
| accent-glow | rgba(217,119,87,0.15) | Glow effects |
| success | #4CAF84 | Positive states |
| warning | #E8A838 | Warning states |
| error | #E05454 | Error states |
| glass-bg | rgba(255,255,255,0.04) | Glass cards/navbar |
| glass-border | rgba(255,255,255,0.08) | Glass borders |

## Typography
Font: Inter (400/500/600/700) via Google Fonts
- Hero headline: 80px / font-bold / tracking-tight / text-[#F5F0EB]
- Page title: text-2xl font-bold text-[#F5F0EB]
- Section heading: text-lg font-semibold text-[#F5F0EB]
- Body: text-sm text-[#A89F95]
- Label / muted: text-xs text-[#6B6560] uppercase tracking-wider

## Component Classes

### Card (app)
```
rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-6
```

### Glass card (landing)
```
rounded-2xl border border-white/8 bg-white/4 backdrop-blur-md p-6
```

### Input
```
w-full rounded-xl border border-[#1e1c1a] bg-[#161412] px-4 py-2.5 text-sm text-[#F5F0EB] placeholder-[#6B6560] focus:border-[#D97757] focus:outline-none transition-colors
```

### Button — primary (solid)
```
rounded-xl bg-[#D97757] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#C9623F] disabled:opacity-50 transition-colors
```

### Button — glass (landing)
```
rounded-xl border border-white/15 bg-white/5 backdrop-blur-sm px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10 transition-colors
```

### Button — ghost (solid dark)
```
rounded-xl border border-white px-5 py-2.5 text-sm font-semibold bg-black text-white hover:bg-white/5 transition-colors
```

### Badge (glass)
```
inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm px-4 py-1.5 text-xs text-[#A89F95]
```

### Navbar (glass)
```
fixed top-0 w-full z-50 border-b border-white/8 bg-black/80 backdrop-blur-xl
```

## Sidebar (app layout)
Width: w-56 | bg: bg-[#0d0c0b]/80 | border-r: border-[#1e1c1a]
- Active: bg-[#D97757]/15 text-[#D97757] font-medium
- Inactive: text-[#6B6560] hover:bg-[#161412] hover:text-[#F5F0EB]

## Animations (Framer Motion)
```
fadeUp: { hidden: { opacity:0, y:24 }, visible: { opacity:1, y:0, transition:{duration:0.5, ease:[0.22,1,0.36,1]} } }
stagger: { visible: { transition: { staggerChildren: 0.1 } } }
```

## Chart Colours (Recharts)
- P90 (bull): #E8906B stroke, dashed
- P50 (base): #D97757 stroke, solid 2px
- P10 (bear): #C9623F stroke, dashed
- Grid: #1e1c1a
- Tooltip: bg #0d0c0b border #2a2520
