import {
  LayoutDashboard,
  ClipboardList,
  Zap,
  Trophy,
  TrendingUp,
  BookOpen,
  Brain,
  Radio,
  Info,
  MessageSquare,
  type LucideIcon,
} from 'lucide-react';

export type NavItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  description?: string;
};

export const mainNavigation: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    href: '/',
    description: 'Overview of your swim meet optimization'
  },
  {
    id: 'meet',
    label: 'Meet Setup',
    icon: ClipboardList,
    href: '/meet',
    description: 'Upload team rosters and configure meet settings'
  },
  {
    id: 'optimize',
    label: 'Optimizer',
    icon: Zap,
    href: '/optimize',
    description: 'Run AI optimization for lineups'
  },
  {
    id: 'results',
    label: 'Results',
    icon: Trophy,
    href: '/results',
    description: 'View and export optimization results'
  },
  {
    id: 'analytics',
    label: 'Analytics',
    icon: TrendingUp,
    href: '/analytics',
    description: 'Team comparison and performance insights'
  },
  {
    id: 'history',
    label: 'History',
    icon: BookOpen,
    href: '/history',
    description: 'Historical meet data, teams, and swimmer profiles'
  },
  {
    id: 'intelligence',
    label: 'Intel',
    icon: Brain,
    href: '/intelligence',
    description: 'AI-powered trajectory, psychological, and coaching analysis'
  },
];

// Championship-only navigation items
export const championshipNavigation: NavItem[] = [
  {
    id: 'live',
    label: 'Live',
    icon: Radio,
    href: '/live',
    description: 'Real-time championship meet tracking'
  },
];

export const secondaryNavigation: NavItem[] = [
  {
    id: 'about',
    label: 'About',
    icon: Info,
    href: '/about',
    description: 'Learn more about AquaForge'
  },
  {
    id: 'contact',
    label: 'Contact',
    icon: MessageSquare,
    href: '/contact',
    description: 'Get support or send feedback'
  },
];

export const allNavigation = [...mainNavigation, ...secondaryNavigation];
