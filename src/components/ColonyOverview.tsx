import React from "react";
import {
  Colony,
  Infrastructure,
  SupportUpgrade,
  Representative,
  ColonyResource,
  ColonyStatsBreakdown,
} from "../types/colony";
import { formatFoundingAge } from "../lib/chronometer";
import {
  Building2,
  Smile,
  ShieldCheck,
  TrendingUp,
  Flame,
  Coins,
  Calendar,
  User,
  ArrowRight,
  Layers,
  Sparkles,
  AlertTriangle,
} from "lucide-react";

interface ColonyOverviewProps {
  colony: Colony;
  stats: ColonyStatsBreakdown;
  infrastructures: Infrastructure[];
  upgrades: SupportUpgrade[];
  representative: Representative | null;
  resources: ColonyResource[];
  onNavigateTab: (tab: any) => void;
}
type ColonyStateFlags = ColonyStatsBreakdown["states"];

function statLabel(
  states: ColonyStateFlags,
  primary: keyof ColonyStateFlags,
  primaryLabel: string,
  secondary: keyof ColonyStateFlags,
  secondaryLabel: string,
  fallback: string,
): string {
  if (states[primary]) return primaryLabel;
  if (states[secondary]) return secondaryLabel;
  return fallback;
}



export const ColonyOverview: React.FC<ColonyOverviewProps> = ({
  colony,
  stats,
  infrastructures,
  upgrades,
  representative,
  resources,
  onNavigateTab,
}) => {
  const age = formatFoundingAge(colony.founding_days || 0);

  const workingInfras = infrastructures.filter((i) => i.state === "working");
  const workingUpgrades = upgrades.filter((u) => u.state === "working");

  const complacencyLabel = statLabel(
    stats.states,
    "isPlacated",
    "PLACATED",
    "hasRiots",
    "RIOTS",
    "NORMAL",
  );
  const orderLabel = statLabel(
    stats.states,
    "isOrderly",
    "ORDERLY",
    "hasAnarchy",
    "ANARCHY",
    "NORMAL",
  );
  const productivityLabel = statLabel(
    stats.states,
    "isProductive",
    "PRODUCTIVE",
    "isHalted",
    "HALTED",
    "NORMAL",
  );
  const pietyLabel = statLabel(
    stats.states,
    "isPious",
    "PIOUS",
    "isHeretical",
    "HERETICAL",
    "DEVOUT",
  );

  const sizeRank = stats.size.final;
  const sizeNames = [
    "Ghost Town",
    "Settlement",
    "Outpost",
    "Freehold",
    "Demesne",
    "Holding",
    "Dominion",
    "Territory",
    "City",
    "Metropolis",
    "Hive",
  ];
  const sizeDescriptor = sizeNames[sizeRank] || `Rank ${sizeRank}`;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Colony Dossier Box */}
      <div className="gothic-bracket-box p-5 sm:p-6 rounded shadow-xl relative">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        {/* Dossier Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-[#222e46] pb-4 mb-4 gap-3">
          <div>
            <h1 className="font-gothic font-bold text-2xl sm:text-3xl text-[#fef08a] tracking-wide uppercase">
              {colony.name}
            </h1>
            <div className="flex items-center space-x-2 text-[#f59e0b] mt-1.5">
              <span className="text-xs font-mono-slate uppercase">
                {colony.star_system ? colony.star_system : "Uncharted System"}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span className="px-3 py-1 bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/30 rounded font-mono-slate text-xs uppercase tracking-wider font-semibold">
              {colony.colony_type.replaceAll("_", " ")}
            </span>
            <button
              id="overview-inspect-charter-button"
              onClick={() => onNavigateTab("details")}
              className="px-3 py-1 bg-[#1e293b] hover:bg-[#334155] text-[#f8fafc] border border-[#475569] rounded font-mono-slate text-xs transition"
            >
              Inspect Charter
            </button>
          </div>
        </div>

        {/* Dossier Meta Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-2 border-b border-[#1e293b] text-xs font-mono-slate">
          <div>
            <span className="text-[#64748b] uppercase block text-[10px] tracking-wider">
              FOUNDING DYNASTY
            </span>
            <span className="text-[#f8fafc] font-semibold">
              {colony.founder_name}
            </span>
          </div>

          <div>
            <span className="text-[#64748b] uppercase block text-[10px] tracking-wider flex items-center space-x-1">
              <Calendar className="w-3 h-3 text-[#f59e0b]" />
              <span>COLONY AGE</span>
            </span>
            <span className="text-[#38bdf8] font-semibold">{age.formatted || `${colony.founding_days || 0} Standard Days`}</span>
          </div>

          <div>
            <span className="text-[#64748b] uppercase block text-[10px] tracking-wider">
              COLONY TYPE
            </span>
            <span className="text-[#cbd5e1] capitalize">
              {colony.colony_type.replaceAll("_", " ")}
            </span>
          </div>

          <div>
            <span className="text-[#64748b] uppercase block text-[10px] tracking-wider flex items-center space-x-1">
              <User className="w-3 h-3 text-[#38bdf8]" />
              <span>REPRESENTATIVE</span>
            </span>
            {representative ? (
              <span className="text-[#34d399] font-semibold block truncate">
                {representative.name}
              </span>
            ) : (
              <>
                <span className="text-[#f87171] text-xs block">Unassigned</span>
                <button
                  onClick={() => onNavigateTab("representative")}
                  className="text-[#38bdf8] hover:text-[#7dd3fc] text-[11px] underline"
                >
                  Assign Representative →
                </button>
              </>
            )}
          </div>
        </div>

        {/* Dossier Bottom Row: Colony Condition Status Badges */}
        <div className="pt-3 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs font-mono-slate">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] text-[#94a3b8] uppercase font-semibold">
              COLONY CONDITION:
            </span>
            <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[11px] uppercase font-bold">
              complacency: {complacencyLabel}
            </span>
            <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[11px] uppercase font-bold">
              order: {orderLabel}
            </span>
            <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[11px] uppercase font-bold">
              productivity: {productivityLabel}
            </span>
            <span className="px-2 py-0.5 bg-[#38bdf8]/15 text-[#38bdf8] border border-[#38bdf8]/40 rounded text-[11px] uppercase font-bold">
              piety: {pietyLabel}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Characteristics & Metric Cards Grid (6 cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Card 1: Colony Size */}
        <div className="stat-card-gold p-4 rounded shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#94a3b8]">
            <span className="text-[10px] font-mono-slate tracking-wider uppercase font-bold">
              COLONY SIZE
            </span>
            <Building2 className="w-4 h-4 text-[#f59e0b]" />
          </div>
          <div className="my-2">
            <div className="text-3xl font-gothic font-bold text-[#fef08a]">
              {stats.size.final}
            </div>
            <div className="text-[11px] font-gothic text-[#cbd5e1] font-semibold uppercase tracking-wider">
              {sizeDescriptor} (Size {stats.size.final})
            </div>
          </div>
          <div className="text-[10px] font-mono-slate text-[#64748b]">
            0-10 Settlement Rank
          </div>
        </div>

        {/* Card 2: Complacency */}
        <div className="stat-card p-4 rounded shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#94a3b8]">
            <span className="text-[10px] font-mono-slate tracking-wider uppercase font-bold">
              COMPLACENCY
            </span>
            <Smile className="w-4 h-4 text-[#38bdf8]" />
          </div>
          <div className="my-2">
            <div className="text-3xl font-gothic font-bold text-[#f8fafc]">
              {stats.complacency.final}
            </div>
            <span className="inline-block mt-0.5 px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[10px] uppercase font-bold tracking-wider">
              {complacencyLabel}
            </span>
          </div>
          <div className="text-[10px] font-mono-slate text-[#64748b]">
            Target: &gt; Size for Placated (+1 PF)
          </div>
        </div>

        {/* Card 3: Order */}
        <div className="stat-card p-4 rounded shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#94a3b8]">
            <span className="text-[10px] font-mono-slate tracking-wider uppercase font-bold">
              ORDER
            </span>
            <ShieldCheck className="w-4 h-4 text-[#a855f7]" />
          </div>
          <div className="my-2">
            <div className="text-3xl font-gothic font-bold text-[#f8fafc]">
              {stats.order.final}
            </div>
            <span className="inline-block mt-0.5 px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[10px] uppercase font-bold tracking-wider">
              {orderLabel}
            </span>
          </div>
          <div className="text-[10px] font-mono-slate text-[#64748b]">
            Target: &gt; Size for Orderly (+2 PF)
          </div>
        </div>

        {/* Card 4: Productivity */}
        <div className="stat-card p-4 rounded shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#94a3b8]">
            <span className="text-[10px] font-mono-slate tracking-wider uppercase font-bold">
              PRODUCTIVITY
            </span>
            <TrendingUp className="w-4 h-4 text-[#10b981]" />
          </div>
          <div className="my-2">
            <div className="text-3xl font-gothic font-bold text-[#f8fafc]">
              {stats.productivity.final}
            </div>
            <span className="inline-block mt-0.5 px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[10px] uppercase font-bold tracking-wider">
              {productivityLabel}
            </span>
          </div>
          <div className="text-[10px] font-mono-slate text-[#64748b]">
            Target: &gt; Size for Productive (+2 PF)
          </div>
        </div>

        {/* Card 5: Piety */}
        <div className="stat-card p-4 rounded shadow-md flex flex-col justify-between">
          <div className="flex items-center justify-between text-[#94a3b8]">
            <span className="text-[10px] font-mono-slate tracking-wider uppercase font-bold">
              PIETY
            </span>
            <Flame className="w-4 h-4 text-[#ef4444]" />
          </div>
          <div className="my-2">
            <div className="text-3xl font-gothic font-bold text-[#f8fafc]">
              {stats.piety.final}
            </div>
            <span className="inline-block mt-0.5 px-2 py-0.5 bg-[#38bdf8]/15 text-[#38bdf8] border border-[#38bdf8]/40 rounded text-[10px] uppercase font-bold tracking-wider">
              {pietyLabel}
            </span>
          </div>
          <div className="text-[10px] font-mono-slate text-[#64748b]">
            Target: &gt; Size for Pious (Holy Favor)
          </div>
        </div>

        {/* Card 6: Profit Factor */}
        <div className="stat-card-gold p-4 rounded shadow-md flex flex-col justify-between bg-gradient-to-b from-[#181d2c] to-[#121624]">
          <div className="flex items-center justify-between text-[#f59e0b]">
            <span className="text-[10px] font-mono-slate tracking-wider uppercase font-bold">
              PROFIT FACTOR
            </span>
            <Coins className="w-4 h-4 text-[#f59e0b]" />
          </div>
          <div className="my-2">
            <div className="text-3xl font-gothic font-bold text-[#fef08a]">
              +{stats.profitFactor.final} PF
            </div>
            <div className="text-[11px] font-mono-slate text-[#34d399] font-semibold">
              TOTAL GENERATION
            </div>
          </div>
          <div className="text-[10px] font-mono-slate text-[#94a3b8] leading-tight">
            Base from Size {stats.size.final}: +{stats.profitFactor.baseFromSize} PF
          </div>
        </div>
      </div>

      {/* 3. Bottom Two-Column Split: Infrastructure Systems & Planetary Natural Resources */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Infrastructure Systems */}
        <div className="gothic-bracket-box p-5 rounded shadow-lg space-y-4">
          <div className="gothic-bracket-bottom-left" />
          <div className="gothic-bracket-bottom-right" />

          <div className="flex items-center justify-between border-b border-[#222e46] pb-3">
            <div>
              <h3 className="font-gothic font-bold text-sm tracking-wider text-[#f59e0b] uppercase flex items-center space-x-2">
                <Layers className="w-4 h-4 text-[#f59e0b]" />
                <span>PLANETARY INFRASTRUCTURE</span>
              </h3>
              <p className="text-[11px] text-[#94a3b8] font-mono-slate">
                {workingInfras.length} Hard Infrastructure • {workingUpgrades.length} Support Upgrades
              </p>
            </div>

            <button
              id="overview-manage-systems-button"
              onClick={() => onNavigateTab("plans")}
              className="text-[#38bdf8] hover:text-[#7dd3fc] text-xs font-mono-slate flex items-center space-x-1"
            >
              <span>Manage Systems</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* 5 Hard Infrastructure Chips */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[
              { type: "transport", label: "Transport" },
              { type: "power_network", label: "Power" },
              { type: "water_management", label: "Water" },
              { type: "food_production", label: "Food Production" },
              { type: "communications", label: "Communications" },
            ].map((hardSys) => {
              const installed = infrastructures.find(
                (i) => i.infrastructure_type === hardSys.type
              );
              const isWorking = installed?.state === "working";

              return (
                <div
                  key={hardSys.type}
                  className={`p-2.5 rounded border text-xs font-mono-slate flex items-center justify-between ${
                    isWorking
                      ? "bg-[#101726] border-[#10b981]/40 text-[#f8fafc]"
                      : "bg-[#0d121f] border-[#222e46] text-[#64748b]"
                  }`}
                >
                  <span className="font-medium">{hardSys.label}</span>
                  <span
                    className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-bold ${
                      isWorking
                        ? "bg-[#10b981]/20 text-[#34d399]"
                        : "bg-[#ef4444]/20 text-[#f87171]"
                    }`}
                  >
                    {installed?.state || "NEEDED"}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Installed Support Upgrades */}
          <div className="pt-2 border-t border-[#1e293b]">
            <div className="flex items-center justify-between text-[11px] font-mono-slate mb-2">
              <span className="text-[#94a3b8] uppercase font-semibold">
                INSTALLED SUPPORT UPGRADES ({upgrades.length} / MAX {stats.size.final})
              </span>
              {upgrades.length > stats.size.final && (
                <span className="text-[#f59e0b] text-[10px] flex items-center space-x-1">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Capped at Size {stats.size.final}</span>
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {upgrades.length > 0 ? (
                upgrades.map((upg) => (
                  <span
                    key={upg.id}
                    className="px-2.5 py-1 bg-[#121929] border border-[#2b3954] text-[#cbd5e1] rounded text-xs font-mono-slate flex items-center space-x-1.5"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]" />
                    <span className="capitalize">{upg.name || upg.upgrade_type.replaceAll("_", " ")}</span>
                    <span className="text-[10px] text-[#64748b]">({upg.state})</span>
                  </span>
                ))
              ) : (
                <span className="text-xs text-[#64748b] font-mono-slate italic">
                  No support upgrades currently commissioned.
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Planetary Natural Resources */}
        <div className="gothic-bracket-box p-5 rounded shadow-lg space-y-4">
          <div className="gothic-bracket-bottom-left" />
          <div className="gothic-bracket-bottom-right" />

          <div className="flex items-center justify-between border-b border-[#222e46] pb-3">
            <div>
              <h3 className="font-gothic font-bold text-sm tracking-wider text-[#f59e0b] uppercase flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-[#f59e0b]" />
                <span>PLANETARY NATURAL RESOURCES</span>
              </h3>
              <p className="text-[11px] text-[#94a3b8] font-mono-slate">
                {resources.length} Surveyed Resource Deposits
              </p>
            </div>

            <button
              id="overview-survey-deposits-button"
              onClick={() => onNavigateTab("details")}
              className="text-[#38bdf8] hover:text-[#7dd3fc] text-xs font-mono-slate flex items-center space-x-1"
            >
              <span>Survey Deposits</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2.5 font-mono-slate text-xs">
            {resources.length > 0 ? (
              resources.map((res) => (
                <div
                  key={res.id}
                  className="p-3 bg-[#0d121f] border border-[#1e293b] rounded flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-[#f8fafc]">{res.name}</span>
                      <span className="text-[10px] text-[#38bdf8] px-1.5 py-0.5 bg-[#38bdf8]/10 rounded border border-[#38bdf8]/30">
                        {res.resource_type || "Mineral"}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#64748b]">
                      {res.description || "Core extraction complex"}
                    </p>
                  </div>

                  <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[11px] font-bold">
                    {res.abundance || "Abundant"}
                  </span>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-[#64748b] italic">
                No planetary natural resources surveyed yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
