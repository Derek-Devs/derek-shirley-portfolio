// src/utils/colors.ts
export const getDaisyUIColor = (semanticName: string, opacity?: number): string => {
  if (typeof window === 'undefined') {
    const fallbackOpacity = opacity === undefined ? 1 : opacity;
    return `hsla(0, 0%, ${fallbackOpacity === 1 ? '20%' : '80%'}, ${fallbackOpacity})`;
  }

  const variableMap: { [key: string]: string } = {
    'p': '--color-primary', 'pc': '--color-primary-content',
    's': '--color-secondary', 'sc': '--color-secondary-content',
    'a': '--color-accent', 'ac': '--color-accent-content',
    'n': '--color-neutral', 'nc': '--color-neutral-content',
    'b1': '--color-base-100', 'b2': '--color-base-200',
    'b3': '--color-base-300', 'bc': '--color-base-content',
    'in': '--color-info', 'inc': '--color-info-content',
    'su': '--color-success', 'suc': '--color-success-content',
    'wa': '--color-warning', 'wac': '--color-warning-content',
    'er': '--color-error', 'erc': '--color-error-content',
  };

  const fullVariableName = variableMap[semanticName] || `--color-${semanticName}`;

  try {
    let colorValue = getComputedStyle(document.documentElement).getPropertyValue(fullVariableName).trim();

    if (colorValue) {
      if (opacity !== undefined && opacity >= 0 && opacity < 1) {
        if (colorValue.startsWith('oklch') || colorValue.startsWith('hsl') || colorValue.startsWith('rgb')) {
          if (!colorValue.includes('/')) {
            const closingParen = colorValue.lastIndexOf(')');
            if (closingParen !== -1) {
              colorValue = `${colorValue.substring(0, closingParen)} / ${opacity})`;
            }
          } else {
            const parts = colorValue.split('/');
            if (parts.length === 2) {
              colorValue = `${parts[0].trim()} / ${opacity})`;
            }
          }
        }
      }
      return colorValue;
    }
  } catch (_error) { // Changed 'error' to '_error' to denote it as intentionally unused
  }
  
  // console.warn(`[ColorUtil] Variable ${fullVariableName} not found. Using fallback.`); // For debugging
  const errorFallbackHue = (semanticName.charCodeAt(0) * 20) % 360;
  const fallbackOpacity = opacity === undefined ? 1 : opacity;
  return `hsla(${errorFallbackHue}, 70%, 50%, ${fallbackOpacity})`;
};