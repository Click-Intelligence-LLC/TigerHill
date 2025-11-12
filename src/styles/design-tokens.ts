/**
 * Design Tokens for TigerHill Dashboard
 * Based on stitch design mockups
 *
 * Usage:
 * import { colorTokens } from '@/styles/design-tokens';
 * const bgColor = colorTokens.light.surface;
 */

export interface ColorMode {
  // Backgrounds
  background: string;
  backgroundSubtle: string;

  // Surfaces (cards, panels)
  surface: string;
  surfaceMuted: string;

  // Text
  textPrimary: string;
  textSecondary: string;
  textMuted: string;

  // Borders
  border: string;
  borderStrong: string;
}

export interface AccentColors {
  primary: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
}

export interface TokenColors {
  input: string;
  output: string;
}

export interface PromptColors {
  system: string;
  history: string;
  context: string;
  toolCall: string;
  user: string;
}

export const colorTokens = {
  // Light Mode
  light: {
    background: '#F6F7F8',
    backgroundSubtle: '#EEF1F5',
    surface: '#FFFFFF',
    surfaceMuted: '#F9FAFB',
    textPrimary: '#111827',
    textSecondary: '#6B7280',
    textMuted: '#9CA3AF',
    border: 'rgba(0, 0, 0, 0.1)',
    borderStrong: 'rgba(0, 0, 0, 0.2)',
  } as ColorMode,

  // Dark Mode
  dark: {
    background: '#101922',
    backgroundSubtle: '#0A0F16',
    surface: 'rgba(0, 0, 0, 0.2)',
    surfaceMuted: 'rgba(0, 0, 0, 0.3)',
    textPrimary: '#FFFFFF',
    textSecondary: '#D1D5DB',
    textMuted: '#9CA3AF',
    border: 'rgba(255, 255, 255, 0.1)',
    borderStrong: 'rgba(255, 255, 255, 0.2)',
  } as ColorMode,

  // Semantic colors (mode-independent)
  accent: {
    primary: '#2B8CEE',
    success: '#22C55E',
    warning: '#FACC15',
    danger: '#F87171',
    info: '#38BDF8',
  } as AccentColors,

  // Token visualization colors
  token: {
    input: '#FACC15',
    output: '#F87171',
  } as TokenColors,

  // Prompt component colors
  prompt: {
    system: '#60A5FA',
    history: '#FCA5A5',
    context: '#86EFAC',
    toolCall: '#C084FC',
    user: '#FBBF24',
  } as PromptColors,
} as const;

/**
 * Helper to get color tokens for current theme
 */
export function getColorMode(isDark: boolean): ColorMode {
  return isDark ? colorTokens.dark : colorTokens.light;
}

/**
 * Component type to color mapping for prompt visualization
 */
export const promptComponentColors: Record<string, string> = {
  system: colorTokens.prompt.system,
  system_instruction: colorTokens.prompt.system,
  conversation_history: colorTokens.prompt.history,
  history: colorTokens.prompt.history,
  environment: colorTokens.prompt.context,
  context: colorTokens.prompt.context,
  tool_call: colorTokens.prompt.toolCall,
  function_call: colorTokens.prompt.toolCall,
  user: colorTokens.prompt.user,
  user_instruction: colorTokens.prompt.user,
};

/**
 * Get color for prompt component type
 */
export function getPromptComponentColor(componentType: string): string {
  return promptComponentColors[componentType] || colorTokens.dark.textMuted;
}

export default colorTokens;
