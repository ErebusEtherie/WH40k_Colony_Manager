import React, { useState } from "react";
import {
  Colony,
  Representative,
  Modifier,
  ColonyResource,
  ColonyStatsBreakdown,
  StatContribution,
} from "../types/colony";
import { formatFoundingAge } from "../lib/chronometer";
import {
  Edit3,
  UserCheck,
  Plus,
  Trash2,
  ArrowRight,
} from "lucide-react";

interface ColonyDetailsViewProps {
  colony: Colony;
  stats: ColonyStatsBreakdown;
  representative: Representative | null;
  modifiers: Modifier[];
  resources: ColonyResource[];
  onAdvanceDays?: (days: number) => void;
  /** Directly sets the colony's age (days since founding), not an additive advance. */
  onSetAge?: (ageDays: number) => void;
  onNavigateTab?: (tab: "representative" | "plans") => void;
  onOpenReassignRep?: () => void;
  onOpenAddModifier: () => void;
  onOpenLogResource: () => void;
  onDeleteModifier: (id: string) => void;
  onToggleModifier: (id: string, active: boolean) => void;
  onDeleteResource: (id: string) => void;
  onOpenEditCharter?: () => void;
  /** Only shown to the system admin (Arch Magos) role. */
  canDelete?: boolean;
  onDeleteColony?: () => void;
}

export const ColonyDetailsView: React.FC<ColonyDetailsViewProps> = ({
  colony,
  stats,
  representative,
  modifiers,
  resources,
  onAdvanceDays,
  onSetAge,
  onNavigateTab,
  onOpenReassignRep,
  onOpenAddModifier,
  onOpenLogResource,
  onDeleteModifier,
  onToggleModifier,
  onDeleteResource,
  onOpenEditCharter,
  canDelete,
  onDeleteColony,
}) => {
  const [customDays, setCustomDays] = useState("30");
  const [setAgeValue, setSetAgeValue] = useState(String(colony.founding_days || 0));
  const age = formatFoundingAge(colony.founding_days || 0);

  const handleCustomAdvance = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    const days = Number.parseInt(customDays, 10);
    if (!Number.isNaN(days) && days > 0) {
      onAdvanceDays(days);
    }
  };

  const handleCustomSet = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    const days = Number.parseInt(setAgeValue, 10);
    if (!Number.isNaN(days) && days >= 0 && onSetAge) {
      onSetAge(days);
    }
  };

  const getComplacencyState = (): string => {
    if (stats.states.isPlacated) return "PLACATED";
    if (stats.states.hasRiots) return "RIOTS";
    return "NORMAL";
  };
  const getOrderState = (): string => {
    if (stats.states.isOrderly) return "ORDERLY";
    if (stats.states.hasAnarchy) return "ANARCHY";
    return "NORMAL";
  };
  const getProductivityState = (): string => {
    if (stats.states.isProductive) return "PRODUCTIVE";
    if (stats.states.isHalted) return "HALTED";
    return "NORMAL";
  };
  const getPietyState = (): string => {
    if (stats.states.isPious) return "PIOUS";
    if (stats.states.isHeretical) return "HERETICAL";
    return "NORMAL";
  };

  const renderAuditList = (contributions: StatContribution[] = []) => {
    if (!contributions || contributions.length === 0) {
      return <div className="text-[#64748b] text-[11px] italic">No active modifiers</div>;
    }
    return (
      <div className="space-y-1 mt-2 font-mono-slate text-xs">
        {contributions.map((c) => (
          <div key={c.source} className="flex items-center justify-between text-[11px] py-0.5 border-b border-[#1c263c]/50">
            <span className="text-[#94a3b8]">{c.source}:</span>
            <span className={`font-semibold ${c.value >= 0 ? "text-[#34d399]" : "text-[#f87171]"}`}>
              {c.value >= 0 ? `+${c.value}` : c.value}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Colony Administrative Record */}
      <div className="gothic-bracket-box p-5 sm:p-6 rounded shadow-xl space-y-4">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#222e46] pb-3">
          <div>
            <h2 className="font-gothic font-bold text-base sm:text-lg tracking-wider text-[#f59e0b] uppercase">
              COLONY ADMINISTRATIVE RECORD
            </h2>
            <p className="text-xs text-[#94a3b8] font-mono-slate mt-0.5">
              Colony Details
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              id="details-edit-charter-button"
              onClick={onOpenEditCharter}
              className="flex items-center space-x-1 px-3 py-1.5 bg-[#121828] hover:bg-[#1a233a] border border-[#f59e0b]/50 text-xs font-mono-slate text-[#fef08a] rounded transition"
            >
              <Edit3 className="w-3.5 h-3.5 text-[#f59e0b]" />
              <span>Edit Charter</span>
            </button>
            {canDelete && (
              <button
                id="details-delete-colony-button"
                onClick={() => {
                  if (
                    window.confirm(
                      `Are you sure you want to dissolve the colony "${colony.name}"? This action cannot be undone.`
                    )
                  ) {
                    onDeleteColony?.();
                  }
                }}
                className="flex items-center space-x-1 px-3 py-1.5 bg-[#2a1113] hover:bg-[#3a1518] border border-[#ef4444]/50 text-xs font-mono-slate text-[#fca5a5] rounded transition"
              >
                <Trash2 className="w-3.5 h-3.5 text-[#ef4444]" />
                <span>Delete Colony</span>
              </button>
            )}
          </div>
        </div>

        {/* Administrative Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono-slate text-xs">
          <div className="p-3 bg-[#0d121f] border border-[#1e293b] rounded space-y-1">
            <span className="text-[10px] text-[#64748b] tracking-wider uppercase block font-semibold">
              DESIGNATION
            </span>
            <span className="font-gothic font-bold text-sm text-[#f8fafc] block">
              {colony.name}
            </span>
          </div>

          <div className="p-3 bg-[#0d121f] border border-[#1e293b] rounded space-y-1">
            <span className="text-[10px] text-[#64748b] tracking-wider uppercase block font-semibold">
              SECTOR / SYSTEM
            </span>
            <span className="font-semibold text-[#38bdf8] text-sm block">
              {colony.star_system || "Uncharted System"}
            </span>
          </div>

          <div className="p-3 bg-[#0d121f] border border-[#1e293b] rounded space-y-1">
            <span className="text-[10px] text-[#64748b] tracking-wider uppercase block font-semibold">
              Founder *
            </span>
            <span className="font-semibold text-[#e2e8f0] text-sm block">
              {colony.founder_name}
            </span>
          </div>

          <div className="p-3 bg-[#0d121f] border border-[#1e293b] rounded space-y-1">
            <span className="text-[10px] text-[#64748b] tracking-wider uppercase block font-semibold">
              COLONY TYPE (FIXED AT CREATION)
            </span>
            <span className="font-gothic font-bold text-sm text-[#fef08a] block capitalize">
              {colony.colony_type.replaceAll("_", " ")}
            </span>
          </div>
        </div>

        {/* Dossier Notes */}
        <div className="p-3 bg-[#0d121f] border border-[#1e293b] rounded text-xs font-mono-slate">
          <span className="text-[10px] text-[#64748b] tracking-wider uppercase block font-semibold mb-1">
            RECORDED COLONY DOSSIER DESCRIPTION
          </span>
          {colony.notes ? (
            <p className="text-[#cbd5e1] italic">{colony.notes}</p>
          ) : (
            <p className="text-[#475569] italic">
              No dossier notes recorded. Use Edit Charter to record the colony's strategic intent.
            </p>
          )}
        </div>

        {/* Colony Age */}
        <div className="p-3.5 bg-[#0f1523] border border-[#23314d] rounded flex flex-col md:flex-row items-start md:items-center justify-between gap-4 font-mono-slate text-xs">
          <div>
            <span className="text-[10px] text-[#f59e0b] tracking-wider uppercase block font-bold">
              COLONY AGE
            </span>
            <div className="flex items-center space-x-2 mt-0.5">
              <span className="text-sm font-bold text-[#f8fafc]">
                {colony.founding_days || 0} standard days
              </span>
              <span className="text-[#64748b]">|</span>
              <span className="text-[#38bdf8] text-xs">
                {age.formatted}
              </span>
            </div>
          </div>

          {/* Advance Time Controls */}
          <div className="flex items-center space-x-2">
            <span className="text-[11px] text-[#94a3b8] uppercase font-semibold">
              ADVANCE AGE:
            </span>
            <button
              id="details-advance-1d"
              onClick={() => onAdvanceDays(1)}
              className="px-2.5 py-1 bg-[#101726] hover:bg-[#19243c] border border-[#23314d] text-[#38bdf8] rounded transition"
              title="Advance Colony Age by 1 Days"
            >
              +1d
            </button>
            <button
              id="details-advance-5d"
              onClick={() => onAdvanceDays(5)}
              className="px-2.5 py-1 bg-[#101726] hover:bg-[#19243c] border border-[#23314d] text-[#38bdf8] rounded transition"
              title="Advance Colony Age by 5 Days"
            >
              +5d
            </button>
            <button
              id="details-advance-10d"
              onClick={() => onAdvanceDays(10)}
              className="px-2.5 py-1 bg-[#101726] hover:bg-[#19243c] border border-[#23314d] text-[#38bdf8] rounded transition"
              title="Advance Colony Age by 10 Days"
            >
              +10d
            </button>

            <form onSubmit={handleCustomAdvance} className="flex items-center space-x-1">
              <input
                id="custom-days-input"
                type="number"
                min="1"
                max="3650"
                value={customDays}
                onChange={(e) => setCustomDays(e.target.value)}
                className="w-14 bg-[#070a12] border border-[#252f44] text-[#f8fafc] px-2 py-1 rounded text-center focus:outline-none focus:border-[#f59e0b]"
              />
              <button
                id="details-advance-custom-submit"
                type="submit"
                className="px-2 py-1 bg-[#f59e0b]/20 hover:bg-[#f59e0b]/30 text-[#fef08a] border border-[#f59e0b]/60 rounded font-bold uppercase"
              >
                + ADD
              </button>
            </form>

            <span className="text-[#64748b]">|</span>
            <form onSubmit={handleCustomSet} className="flex items-center space-x-1">
              <input
                id="set-age-input"
                type="number"
                min="0"
                max="3650000"
                value={setAgeValue}
                onChange={(e) => setSetAgeValue(e.target.value)}
                className="w-14 bg-[#070a12] border border-[#252f44] text-[#f8fafc] px-2 py-1 rounded text-center focus:outline-none focus:border-[#38bdf8]"
              />
              <button
                id="details-set-age-submit"
                type="submit"
                className="px-2 py-1 bg-[#38bdf8]/15 hover:bg-[#38bdf8]/25 text-[#38bdf8] border border-[#38bdf8]/50 rounded font-bold uppercase"
              >
                SET
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* 2. Colony Representative Dossier */}
      <div className="gothic-bracket-box p-5 sm:p-6 rounded shadow-xl space-y-4">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#222e46] pb-3">
          <div>
            <h2 className="font-gothic font-bold text-base tracking-wider text-[#f59e0b] uppercase">
              COLONY REPRESENTATIVE DOSSIER
            </h2>
            <p className="text-xs text-[#94a3b8] font-mono-slate mt-0.5">
              Assigned Overseer
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              id="details-reassign-rep-button"
              onClick={onOpenReassignRep}
              className="flex items-center space-x-1 px-3 py-1.5 bg-[#121828] hover:bg-[#1a233a] border border-[#23314d] hover:border-[#f59e0b]/50 text-xs font-mono-slate text-[#cbd5e1] rounded transition"
            >
              <UserCheck className="w-3.5 h-3.5 text-[#38bdf8]" />
              <span>Reassign Representative</span>
            </button>

            <button
              id="details-view-full-rep-sheet-button"
              onClick={() => onNavigateTab("representative")}
              className="flex items-center space-x-1 px-3 py-1.5 bg-[#f59e0b]/15 hover:bg-[#f59e0b]/25 border border-[#f59e0b]/60 text-xs font-mono-slate text-[#fef08a] rounded transition"
            >
              <span>Full Sheet</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {representative ? (
          <div className="p-4 bg-[#0d121f] border border-[#1e293b] rounded space-y-3 font-mono-slate text-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#1b253b] pb-2.5">
              <div>
                <span className="font-gothic font-bold text-sm text-[#fef08a] block">
                  {representative.name}
                </span>
                <span className="text-[#38bdf8] text-xs capitalize">
                  {representative.title || representative.representative_type} (
                  {representative.personality || "Scholarly"})
                </span>
              </div>

              <div className="text-right">
                <span className="text-[10px] text-[#64748b] uppercase block">Special Mechanics</span>
                <span className="text-xs text-[#94a3b8]">
                  {representative.special_mechanics || "None / +5 bonus to Acquisition Tests"}
                </span>
              </div>
            </div>

            {/* Characteristics Compact Bar */}
            {representative.characteristics && (
              <div className="grid grid-cols-5 sm:grid-cols-9 gap-1.5 text-center text-[10px]">
                {Object.entries(representative.characteristics).map(([key, val]) => (
                  <div key={key} className="p-1.5 bg-[#090d16] border border-[#1a2337] rounded">
                    <span className="text-[#64748b] uppercase font-bold block">{key}</span>
                    <span className="text-[#f8fafc] font-bold">{val}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Personality Traits */}
            {representative.personality_traits && representative.personality_traits.length > 0 && (
              <div className="pt-2">
                <span className="text-[10px] text-[#64748b] uppercase font-semibold block mb-1.5">
                  Personality Traits ({representative.personality_traits.length})
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {representative.personality_traits.map((trait) => (
                    <div
                      key={trait.id}
                      className="p-2 bg-[#090d16] border border-[#1b253b] rounded text-[11px] space-y-0.5"
                    >
                      <div className="flex items-center space-x-1.5">
                        <span className="font-bold text-[#fef08a]">{trait.name}</span>
                        {trait.stat_tag && (
                          <span className="text-[9px] px-1 py-0.2 bg-[#38bdf8]/15 text-[#38bdf8] rounded border border-[#38bdf8]/30">
                            {trait.stat_tag}
                          </span>
                        )}
                      </div>
                      <p className="text-[#94a3b8]">{trait.description}</p>
                      {trait.effect && (
                        <p className="text-[#34d399] text-[10px] font-semibold">
                          Effect: {trait.effect}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 text-center text-xs text-[#64748b] font-mono-slate italic bg-[#0d121f] rounded border border-[#1e293b]">
            No representative currently assigned to this colony.
          </div>
        )}
      </div>

      {/* 3. Colony Characteristics Modifier Audit (6 columns) */}
      <div className="gothic-bracket-box p-5 sm:p-6 rounded shadow-xl space-y-4">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        <div className="border-b border-[#222e46] pb-3">
          <h2 className="font-gothic font-bold text-base sm:text-lg tracking-wider text-[#f59e0b] uppercase">
            COLONY CHARACTERISTICS MODIFIER AUDIT
          </h2>
          <p className="text-xs text-[#94a3b8] font-mono-slate mt-0.5">
            Transparent breakdown of Base, Permanent, Conditional, and Custom modifiers for all 6 stats
          </p>
        </div>

        {/* 6 Modifier Breakdown Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 font-mono-slate text-xs">
          {/* Complacency Audit */}
          <div className="p-4 bg-[#0d121f] border border-[#1e293b] rounded space-y-2">
            <div className="flex items-center justify-between border-b border-[#1b253b] pb-2">
              <div>
                <span className="font-bold text-sm text-[#f8fafc] block">COMPLACENCY</span>
                <span className="text-[10px] text-[#34d399] uppercase font-bold">
                  {getComplacencyState()}
                </span>
              </div>
              <span className="text-2xl font-gothic font-bold text-[#38bdf8]">
                {stats.complacency.final}
              </span>
            </div>
            {renderAuditList(stats.complacency.contributions)}
          </div>

          {/* Order Audit */}
          <div className="p-4 bg-[#0d121f] border border-[#1e293b] rounded space-y-2">
            <div className="flex items-center justify-between border-b border-[#1b253b] pb-2">
              <div>
                <span className="font-bold text-sm text-[#f8fafc] block">ORDER</span>
                <span className="text-[10px] text-[#34d399] uppercase font-bold">
                  {getOrderState()}
                </span>
              </div>
              <span className="text-2xl font-gothic font-bold text-[#a855f7]">
                {stats.order.final}
              </span>
            </div>
            {renderAuditList(stats.order.contributions)}
          </div>

          {/* Productivity Audit */}
          <div className="p-4 bg-[#0d121f] border border-[#1e293b] rounded space-y-2">
            <div className="flex items-center justify-between border-b border-[#1b253b] pb-2">
              <div>
                <span className="font-bold text-sm text-[#f8fafc] block">PRODUCTIVITY</span>
                <span className="text-[10px] text-[#34d399] uppercase font-bold">
                  {getProductivityState()}
                </span>
              </div>
              <span className="text-2xl font-gothic font-bold text-[#10b981]">
                {stats.productivity.final}
              </span>
            </div>
            {renderAuditList(stats.productivity.contributions)}
          </div>

          {/* Piety Audit */}
          <div className="p-4 bg-[#0d121f] border border-[#1e293b] rounded space-y-2">
            <div className="flex items-center justify-between border-b border-[#1b253b] pb-2">
              <div>
                <span className="font-bold text-sm text-[#f8fafc] block">PIETY</span>
                <span className="text-[10px] text-[#38bdf8] uppercase font-bold">
                  {getPietyState()}
                </span>
              </div>
              <span className="text-2xl font-gothic font-bold text-[#ef4444]">
                {stats.piety.final}
              </span>
            </div>
            {renderAuditList(stats.piety.contributions)}
          </div>

          {/* Colony Size Audit */}
          <div className="p-4 bg-[#0d121f] border border-[#1e293b] rounded space-y-2">
            <div className="flex items-center justify-between border-b border-[#1b253b] pb-2">
              <div>
                <span className="font-bold text-sm text-[#f8fafc] block">COLONY SIZE (CAPPED 0-10)</span>
                <span className="text-[10px] text-[#f59e0b] uppercase font-bold">
                  Settlement Rank {stats.size.final}
                </span>
              </div>
              <span className="text-2xl font-gothic font-bold text-[#fef08a]">
                {stats.size.final}
              </span>
            </div>
            {renderAuditList(stats.size.contributions)}
          </div>

          {/* Profit Factor Audit */}
          <div className="p-4 bg-[#141a29] border border-[#f59e0b]/40 rounded space-y-2">
            <div className="flex items-center justify-between border-b border-[#25324d] pb-2">
              <div>
                <span className="font-bold text-sm text-[#fef08a] block">PROFIT FACTOR</span>
                <span className="text-[10px] text-[#34d399] uppercase font-bold">
                  Calculated Yield
                </span>
              </div>
              <span className="text-2xl font-gothic font-bold text-[#fef08a]">
                +{stats.profitFactor.final} PF
              </span>
            </div>
            {renderAuditList(stats.profitFactor.contributions || [
              { source: `Base from Size ${stats.size.final}`, value: stats.profitFactor.baseFromSize },
              { source: "Placated Bonus", value: stats.profitFactor.placatedBonus },
              { source: "Productive Bonus", value: stats.profitFactor.productiveBonus },
              { source: "Orderly Bonus", value: stats.profitFactor.orderlyBonus },
              { source: "Leadership Modifier", value: stats.profitFactor.leadershipModifier },
              { source: "Custom / Resource Modifiers", value: stats.profitFactor.modifiersTotal },
            ])}
          </div>
        </div>
      </div>

      {/* 4. Custom GM Modifiers Management */}
      <div className="gothic-bracket-box p-5 sm:p-6 rounded shadow-xl space-y-4">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#222e46] pb-3">
          <div>
            <h2 className="font-gothic font-bold text-base tracking-wider text-[#f59e0b] uppercase">
              CUSTOM GM MODIFIERS MANAGEMENT
            </h2>
            <p className="text-xs text-[#94a3b8] font-mono-slate mt-0.5">
              Event outcomes and custom situational bonuses/penalties
            </p>
          </div>

          <button
            id="details-add-custom-modifier-button"
            onClick={onOpenAddModifier}
            className="flex items-center space-x-1 px-3 py-1.5 bg-[#f59e0b]/15 hover:bg-[#f59e0b]/25 border border-[#f59e0b]/60 text-xs font-mono-slate text-[#fef08a] rounded transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Custom Modifier</span>
          </button>
        </div>

        {/* Custom Modifiers Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono-slate text-xs">
            <thead>
              <tr className="border-b border-[#1e293b] text-[#64748b] uppercase text-[10px] tracking-wider">
                <th className="pb-2 pl-2">Status</th>
                <th className="pb-2">Modifier Name & Description</th>
                <th className="pb-2">Target Stat</th>
                <th className="pb-2">Value</th>
                <th className="pb-2">Source</th>
                <th className="pb-2 text-right pr-2">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#172033]">
              {modifiers.length > 0 ? (
                modifiers.map((mod) => (
                  <tr key={mod.id} className="hover:bg-[#0f1422] transition">
                    <td className="py-2.5 pl-2">
                      <button
                        onClick={() => onToggleModifier(mod.id, !mod.is_active)}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase transition ${
                          mod.is_active
                            ? "bg-[#10b981]/20 text-[#34d399] border border-[#10b981]/40"
                            : "bg-[#64748b]/20 text-[#94a3b8] border border-[#64748b]/40"
                        }`}
                      >
                        {mod.is_active ? "Active" : "Inactive"}
                      </button>
                    </td>
                    <td className="py-2.5">
                      <span className="font-semibold text-[#f8fafc] block">{mod.name}</span>
                      {mod.description && (
                        <span className="text-[11px] text-[#64748b] block">{mod.description}</span>
                      )}
                    </td>
                    <td className="py-2.5">
                      <span className="px-1.5 py-0.5 bg-[#121929] border border-[#23314d] text-[#38bdf8] rounded text-[10px] uppercase font-bold">
                        {mod.modifier_stat}
                      </span>
                    </td>
                    <td className="py-2.5">
                      <span
                        className={`font-bold ${
                          mod.modifier_value >= 0 ? "text-[#34d399]" : "text-[#f87171]"
                        }`}
                      >
                        {mod.modifier_value >= 0 ? `+${mod.modifier_value}` : mod.modifier_value}
                      </span>
                    </td>
                    <td className="py-2.5 text-[#94a3b8] text-[11px]">{mod.source || "GM Ruling"}</td>
                    <td className="py-2.5 text-right pr-2">
                      <button
                        onClick={() => onDeleteModifier(mod.id)}
                        className="p-1 text-[#64748b] hover:text-[#f87171] rounded transition"
                        title="Delete Modifier"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-xs text-[#64748b] italic">
                    No custom modifiers recorded. Use the button to add GM modifiers.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Planetary Resources Survey */}
      <div className="gothic-bracket-box p-5 sm:p-6 rounded shadow-xl space-y-4">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#222e46] pb-3">
          <div>
            <h2 className="font-gothic font-bold text-base tracking-wider text-[#f59e0b] uppercase">
              PLANETARY RESOURCES SURVEY
            </h2>
            <p className="text-xs text-[#94a3b8] font-mono-slate mt-0.5">
              Natural resources, minerals, and archeotech available to the colony
            </p>
          </div>

          <button
            id="details-log-deposit-button"
            onClick={onOpenLogResource}
            className="flex items-center space-x-1 px-3 py-1.5 bg-[#f59e0b]/15 hover:bg-[#f59e0b]/25 border border-[#f59e0b]/60 text-xs font-mono-slate text-[#fef08a] rounded transition"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Log Deposit</span>
          </button>
        </div>

        {/* Resources Cards List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono-slate text-xs">
          {resources.length > 0 ? (
            resources.map((res) => (
              <div
                key={res.id}
                className="p-3.5 bg-[#0d121f] border border-[#1e293b] rounded flex items-start justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm text-[#f8fafc]">{res.name}</span>
                    <span className="text-[10px] text-[#38bdf8] px-1.5 py-0.5 bg-[#38bdf8]/10 rounded border border-[#38bdf8]/30">
                      {res.resource_type || "Mineral"}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#64748b]">{res.description}</p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40 rounded text-[11px] font-bold">
                    {res.abundance || "Abundant"}
                  </span>
                  <button
                    onClick={() => onDeleteResource(res.id)}
                    className="p-1 text-[#64748b] hover:text-[#f87171] rounded transition"
                    title="Remove Resource Deposit"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-2 p-4 text-center text-xs text-[#64748b] italic">
              No surveyed natural resource deposits recorded.
            </div>
          )}
        </div>
      </div>

      {/* 6. Callout Banner to Infrastructure */}
      <div className="p-4 bg-[#0c101a] border border-[#f59e0b]/40 rounded-lg flex flex-col sm:flex-row items-center justify-between gap-4 font-mono-slate">
        <div className="text-center sm:text-left">
          <span className="font-gothic font-bold text-xs tracking-wider text-[#fef08a] uppercase block">
            LOOKING TO CONFIGURE HARD INFRASTRUCTURE, SUPPORT UPGRADES, OR DEVELOPMENT PLANS?
          </span>
          <span className="text-[11px] text-[#94a3b8]">
            Manage colony infrastructure upgrades and long-term construction plans.
          </span>
        </div>

        <button
          id="details-goto-infrastructure-button"
          onClick={() => onNavigateTab("plans")}
          className="px-4 py-2 bg-gradient-to-r from-[#b45309] to-[#f59e0b] hover:from-[#d97706] hover:to-[#fcd34d] text-[#06080e] font-gothic font-bold text-xs uppercase tracking-wider rounded transition shadow-md whitespace-nowrap"
        >
          Open Infrastructure Group →
        </button>
      </div>
    </div>
  );
};
