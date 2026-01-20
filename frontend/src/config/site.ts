export const siteConfig = {
  name: 'AquaForge',
  description: 'AI-powered swim meet lineup optimization for competitive advantage',
  version: 'v1.0.0-next',
  theme: {
    colors: {
      primary: 'navy', // Handled by CSS variables
      accent: 'gold',  // Handled by CSS variables
    }
  },
  links: {
    github: 'https://github.com/aquaforge', // Placeholder
    docs: '/docs',
  },
  contact: {
    email: 'support@aquaforge.ai',
  }
};

export const meetModes = [
  { id: 'dual', label: '🏊 Dual Meet', description: 'Head-to-head competition' },
  { id: 'championship', label: '🏆 Champs', description: 'Multi-team championship meet' },
] as const;

export type MeetMode = typeof meetModes[number]['id'];
