import {
  Archive,
  CircleAlert,
  Ellipsis,
  Euro,
  Film,
  House,
  LayoutGrid,
  ListChecks,
  LogOut,
  MonitorPlay,
  Network,
  Search,
  Server,
  Settings,
  Smile,
  Sparkles,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import type { IconName } from "@/lib/nav";

/** Navigatie-iconen (lucide, vaste koppeling ONTWERPTAAL §7). */
export const NAV_ICON: Record<IconName, LucideIcon> = {
  home: House,
  apps: LayoutGrid,
  alert: CircleAlert,
  ai: Sparkles,
  more: Ellipsis,
  server: Server,
  media: Film,
  house: House,
  network: Network,
  flow: Workflow,
  backup: Archive,
  costs: Euro,
  settings: Settings,
  wizard: ListChecks,
  logout: LogOut,
  kijken: MonitorPlay,
  zoeken: Search,
  ik: Smile,
};

