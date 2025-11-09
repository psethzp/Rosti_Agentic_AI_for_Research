# Apple-Inspired Color Scheme

## Overview
The website now uses a simplified, Apple-inspired color palette with only 4 primary colors and their variations. This creates a cleaner, more professional look that's easier on the eyes.

## Color Palette

### Primary Colors
1. **Navy Blue (#273c75)** - Primary accent color
   - Used for: Headers, buttons, primary actions, insights
   - Tailwind class: `text-primary`, `bg-primary`, `border-primary`
   - Lighter variant: `primary-light` (#487eb0)

2. **White (#FFFFFF)** - Main text and highlights
   - Used for: Primary text, headers within cards
   - Tailwind class: `text-white`

3. **Red (#e84118 / #c23616)** - Warnings and challenges
   - Used for: Challenge indicators, error states, PDF icons
   - Tailwind class: `text-accent-red`, `bg-accent-red`, `border-accent-red`
   - Darker variant: #c23616

4. **Gold (#e1b12c)** - Success and insights
   - Used for: Success states, insights, confidence indicators
   - Tailwind class: `text-accent-gold`, `bg-accent-gold`, `border-accent-gold`

### Supporting Colors
- **Dark Background (#353b48)** - Main background
  - Tailwind class: `bg-dark`
  
- **Dark Card (#44515e)** - Card backgrounds
  - Tailwind class: `bg-dark-card`
  - Darker variant: #2d3436 (`bg-dark-darker`)
  
- **Dark Borders (#6c7a89)** - Subtle borders
  - Tailwind class: `border-dark-lighter`
  
- **Light Gray (#dcdde1)** - Secondary text
  - Tailwind class: `text-light`
  - Subtle variant: `text-light-subtle` (opacity 70%)

## Color Usage Guide

### Insights Section
- Container: `bg-dark-card` with `border-dark-lighter`
- Hover: `hover:border-accent-gold`
- Icon button: `bg-accent-gold/20` with `text-accent-gold`
- Confidence: `text-accent-gold`

### Challenges Section
- Container: `bg-dark-card` with `border-dark-lighter`
- Hover: `hover:border-accent-red`
- Icon button: `bg-accent-red/20` with `text-accent-red`
- Severity badges: Dynamic based on severity level

### Next Steps Section
- Container: `bg-dark-card` with `border-dark-lighter`
- Hover: Dynamic based on tag type
- Tag-based colors:
  - Hypothesis: `primary`
  - NextStep: `accent-gold`
  - Clarification: `accent-red`

### Modals
- Background: `bg-dark` overlay
- Content: `bg-dark-card`
- Headers: Context-specific (gold for insights, red for challenges)
- Claims: `border-l-4` with context color
- Citations: Hover `border-primary` or context color

### Buttons
- Primary actions: `bg-primary` with `hover:bg-primary-light`
- Close buttons: `hover:bg-white/10`
- Icon buttons: `bg-{color}/20` with `hover:bg-{color}/30`

## Migration Summary

### Removed Colors
- ❌ Indigo (#4f46e5, #6366f1, etc.)
- ❌ Purple (#7c3aed, #8b5cf6, etc.)
- ❌ Green (#10b981, #22c55e, etc.) - except for specific success states
- ❌ Blue (#3b82f6, #60a5fa, etc.) - replaced with navy
- ❌ Orange (#f97316, #fb923c, etc.)
- ❌ Yellow (#eab308, #facc15, etc.) - replaced with gold
- ❌ Multiple gradient combinations

### Updated Files
1. **base.html**
   - Added Tailwind custom color configuration
   - Updated header from gradient to solid primary

2. **result.html**
   - Updated all section headers and containers
   - Migrated processing status indicators
   - Updated modal HTML structures
   - Modified CSS animations and badges
   - Updated JavaScript render functions (renderInsights, renderChallenges, renderActions)
   - Updated modal population functions (openInsightModal, openChallengeModal, openActionModal)
   - Updated error states and PDF viewer

3. **index.html**
   - Updated hero section text colors
   - Changed form card from gradient header to solid primary
   - Updated textarea and input borders
   - Modified file upload zone colors
   - Updated feature cards with new accent colors
   - Changed drag-and-drop interactions

## Before & After

### Before
- 8+ different color families (indigo, purple, green, red, blue, orange, yellow, gray)
- Multiple gradient combinations
- Inconsistent color usage across sections

### After
- 4 primary colors with minimal variations
- Solid colors throughout (no gradients)
- Consistent, semantic color usage
- Apple-like minimalist aesthetic

## Benefits
1. **Visual Clarity** - Fewer colors reduce visual noise
2. **Professional Look** - Mimics Apple's design philosophy
3. **Better Accessibility** - High contrast with dark backgrounds
4. **Easier Maintenance** - Centralized color system via Tailwind config
5. **Semantic Meaning** - Colors have clear purposes (red=warnings, gold=success, etc.)
