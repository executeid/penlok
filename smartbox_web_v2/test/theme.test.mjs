import assert from 'node:assert/strict'
import tailwindConfig from '../tailwind.config.js'

// ponytail: Static assertions verify design tokens match DESIGN_WEB.md. Add visual regression tests if CI supports headless chrome.
const { theme } = tailwindConfig

// 1. Verify exact TerminalUI colors
const colors = theme.extend.colors
assert.equal(colors.primary, '#00FF41', 'primary color must be #00FF41')
assert.equal(colors.secondary, '#FF6600', 'secondary color must be #FF6600')
assert.equal(colors.tertiary, '#00BFFF', 'tertiary color must be #00BFFF')
assert.equal(colors.background, '#0D0D0D', 'background color must be #0D0D0D')
assert.equal(colors.surface, '#141414', 'surface color must be #141414')
assert.equal(colors.error, '#FF0040', 'error color must be #FF0040')

// 2. Verify 0px border-radius everywhere
for (const [key, value] of Object.entries(theme.borderRadius)) {
  assert.equal(value, '0px', `borderRadius.${key} must be 0px`)
}

// 3. Verify no box-shadows
for (const [key, value] of Object.entries(theme.boxShadow)) {
  assert.equal(value, 'none', `boxShadow.${key} must be none`)
}

// 4. Verify monospace typography
assert.ok(theme.fontFamily.mono[0].includes('JetBrains Mono'), 'fontFamily.mono must use JetBrains Mono')

// 5. Verify scanline background exists
assert.ok(theme.extend.backgroundImage.scanline.includes('repeating-linear-gradient'), 'scanline background must be defined')

console.log('PASS: All TerminalUI theme constraints verified.')
