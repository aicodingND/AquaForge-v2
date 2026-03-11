export type NavItem = {
  id: string;
  label: string;
  icon: string;
  href: string;
  description?: string;
};

export const mainNavigation: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: '📊',
    href: '/',
    description: 'Overview of your swim meet optimization'
  },
  {
    id: 'meet',
    label: 'Meet Setup',
    icon: '📋',
    href: '/meet',
    description: 'Upload team rosters and configure meet settings'
  },
  {
    id: 'optimize',
    label: 'Optimizer',
    icon: '⚡',
    href: '/optimize',
    description: 'Run AI optimization for lineups'
  },
  {
    id: 'results',
    label: 'Results',
    icon: '🏆',
    href: '/results',
    description: 'View and export optimization results'
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: '📈',
    href: '/analytics',
    description: 'Team comparison and performance insights'
  },
  {
    id: 'history',
    label: 'History',
    icon: '📚',
    href: '/history',
    description: 'Historical meet data, teams, and swimmer profiles'
  },
  {
    id: 'intelligence',
    label: 'Intel',
    icon: '🧠',
    href: '/intelligence',
    description: 'AI-powered trajectory, psychological, and coaching analysis'
  },
];

// Championship-only navigation items
export const championshipNavigation: NavItem[] = [
  {
    id: 'live',
    label: 'Live',
    icon: '🔴',
    href: '/live',
    description: 'Real-time championship meet tracking'
  },
];

export const secondaryNavigation: NavItem[] = [
  {
    id: 'about',
    label: 'About',
    icon: 'ℹ️',
    href: '/about',
    description: 'Learn more about AquaForge'
  },
  {
    id: 'contact',
    label: 'Contact',
    icon: '💬',
    href: '/contact',
    description: 'Get support or send feedback'
  },
];

export const allNavigation = [...mainNavigation, ...secondaryNavigation];
