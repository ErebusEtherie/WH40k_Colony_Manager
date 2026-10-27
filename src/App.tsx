import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Colony,
  Representative,
  Infrastructure,
  SupportUpgrade,
  Modifier,
  ColonyResource,
  DevelopmentPlan,
  OpticsSettings,
  ThemeId,
} from "./types/colony";
import { useCurrentUser, useLogout, apiFetch } from "./lib/api";
import {
  INITIAL_COLONIES,
  INITIAL_REPRESENTATIVES,
  INITIAL_INFRASTRUCTURES,
  INITIAL_UPGRADES,
  INITIAL_MODIFIERS,
  INITIAL_RESOURCES,
  INITIAL_PLANS,
} from "./data/seedData";
import { calculateColonyStats } from "./lib/statCalculator";
import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import { ColonyOverview } from "./components/ColonyOverview";
import { ColonyDetailsView } from "./components/ColonyDetailsView";
import { RepresentativeView } from "./components/RepresentativeView";
import { InfrastructurePlansView } from "./components/InfrastructurePlansView";
import { LoginScreen } from "./components/LoginScreen";

// Modals
import { NewColonyModal } from "./components/modals/NewColonyModal";
import { CommissionRepresentativeModal } from "./components/modals/CommissionRepresentativeModal";
import { ReassignRepresentativeModal } from "./components/modals/ReassignRepresentativeModal";
import { CommissionHardInfrastructureModal } from "./components/modals/CommissionHardInfrastructureModal";
import { AddSupportUpgradeModal } from "./components/modals/AddSupportUpgradeModal";
import { AddBlueprintModal } from "./components/modals/AddBlueprintModal";
import { AddCustomModifierModal } from "./components/modals/AddCustomModifierModal";
import { LogResourceDepositModal } from "./components/modals/LogResourceDepositModal";
import { EditCharterModal } from "./components/modals/EditCharterModal";

export function App() {
  const queryClient = useQueryClient();
  // Use TanStack Query for authentication state
  const { data: currentUser, isLoading: authLoading } = useCurrentUser();
  const logoutMutation = useLogout();
  
  const isLoggedIn = !!currentUser;
  
  // Global App States
  const [colonies, setColonies] = useState<Colony[]>([]);
  const [selectedColonyId, setSelectedColonyId] = useState<string>("");

  // Tracks whether the initial backend sync has completed, so we don't flash an
  // empty/demo dashboard while real colonies are still loading.
  const [coloniesLoaded, setColoniesLoaded] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "overview" | "details" | "infrastructure" | "representatives"
  >("overview");

  const [representatives, setRepresentatives] = useState<Representative[]>([]);
  const [selectedRepId, setSelectedRepId] = useState<string>("");

  const [infrastructures, setInfrastructures] = useState<Infrastructure[]>([]);
  const [upgrades, setUpgrades] = useState<SupportUpgrade[]>([]);
  const [modifiers, setModifiers] = useState<Modifier[]>([]);
  const [resources, setResources] = useState<ColonyResource[]>([]);
  const [plans, setPlans] = useState<DevelopmentPlan[]>([]);

  // Visual Theme & Accessibility
  const [theme, setTheme] = useState<ThemeId>("canonical");

  const [opticsSettings, setOpticsSettings] = useState<OpticsSettings>({
    high_contrast: false,
    large_text: false,
    dyslexia_font: false,
    crt_flicker: true,
    audio_chimes: true,
    color_blind_mode: "default",
    display_scale: "100",
  });

  // Visual theme & optics are applied to `document.body` — the selectors in
  // index.css target `body.theme-*` / `body.optics-*` — keyed off App state so
  // toggling them in the Header actually re-themes the page.
  useEffect(() => {
    const body = document.body;
    const knownClasses = [
      "theme-canonical", "theme-dataslate", "theme-forge", "theme-voidfarer",
      "theme-inquisition", "theme-auspex", "theme-parchment",
      "optics-dyslexic", "optics-highcontrast",
      "optics-cb-monochrome", "optics-cb-deuteranopia", "optics-cb-tritanopia",
      "optics-scale-115", "optics-scale-130",
    ];
    knownClasses.forEach((cls) => body.classList.remove(cls));

    body.classList.add(`theme-${theme}`);
    if (opticsSettings.dyslexia_font) body.classList.add("optics-dyslexic");
    if (opticsSettings.high_contrast) body.classList.add("optics-highcontrast");
    if (opticsSettings.color_blind_mode !== "default")
      body.classList.add(`optics-cb-${opticsSettings.color_blind_mode}`);
    if (opticsSettings.display_scale !== "100")
      body.classList.add(`optics-scale-${opticsSettings.display_scale}`);
  }, [theme, opticsSettings]);

  // Merge partial optics updates (legibility toggles send one field at a time).
  const updateOpticsSettings = (patch: Partial<OpticsSettings>) =>
    setOpticsSettings((prev) => ({ ...prev, ...patch }));

  // Modals state
  const [isNewColonyOpen, setIsNewColonyOpen] = useState(false);
  const [isCommissionRepOpen, setIsCommissionRepOpen] = useState(false);
  const [isReassignRepOpen, setIsReassignRepOpen] = useState(false);
  const [isCommissionSystemOpen, setIsCommissionSystemOpen] = useState(false);
  const [isInstallUpgradeOpen, setIsInstallUpgradeOpen] = useState(false);
  const [isAddBlueprintOpen, setIsAddBlueprintOpen] = useState(false);
  const [isAddModifierOpen, setIsAddModifierOpen] = useState(false);
  const [isLogResourceOpen, setIsLogResourceOpen] = useState(false);
  const [isEditCharterOpen, setIsEditCharterOpen] = useState(false);

  // Helper function to fetch and update colony details
  const fetchColonyDetails = async (colony: Colony) => {
    try {
      const res = await apiFetch(`/api/v1/colonies/${colony.id}`);
      if (!res.ok) return;
      const details = await res.json();
      if (!details) return;

      if (Array.isArray(details.infrastructure) && details.infrastructure.length > 0) {
        setInfrastructures((prev) => [
          ...prev.filter((i) => i.colony_id !== colony.id),
          ...details.infrastructure,
        ]);
      }
      if (Array.isArray(details.upgrades) && details.upgrades.length > 0) {
        setUpgrades((prev) => [
          ...prev.filter((u) => u.colony_id !== colony.id),
          ...details.upgrades,
        ]);
      }
      if (Array.isArray(details.modifiers) && details.modifiers.length > 0) {
        setModifiers((prev) => [
          ...prev.filter((m) => m.colony_id !== colony.id),
          ...details.modifiers,
        ]);
      }
      if (Array.isArray(details.resources) && details.resources.length > 0) {
        setResources((prev) => [
          ...prev.filter((r) => r.colony_id !== colony.id),
          ...details.resources,
        ]);
      }
      if (Array.isArray(details.plans) && details.plans.length > 0) {
        setPlans((prev) => [
          ...prev.filter((p) => p.colony_id !== colony.id),
          ...details.plans,
        ]);
      }
    } catch (err) {
      console.log(`Fetch colony ${colony.id} details error:`, err);
    }
  };

  // Sync Data with Backend on initial load (only when logged in)
  useEffect(() => {
    // Only fetch data if user is authenticated
    if (!isLoggedIn) {
      setColoniesLoaded(false);
      return;
    }

    const loadInitialData = async () => {
      try {
        const res = await apiFetch("/api/v1/colonies");
        if (res.ok) {
          const payload = await res.json();
          // The list endpoint returns a paginated envelope { items, meta }; guard
          // for both that and a bare array in case the shape ever changes.
          const coloniesList: Colony[] = Array.isArray(payload)
            ? payload
            : (payload?.items ?? []);

          if (coloniesList.length > 0) {
            setColonies(coloniesList.map(toColonyWithAge));
            if (!coloniesList.some((c) => c.id === selectedColonyId)) {
              setSelectedColonyId(coloniesList[0].id);
            }

            // Fetch nested details for each colony
            coloniesList.forEach((c) => {
              fetchColonyDetails(c);
            });
          }
        }
      } catch (err) {
        console.log("Initial fetch colonies error:", err);
      }

      try {
        const res = await apiFetch("/api/v1/representatives");
        if (res.ok) {
          const payload = await res.json();
          const data: Representative[] = Array.isArray(payload)
            ? payload
            : (payload?.items ?? []);
          if (data.length > 0) {
            setRepresentatives(data);
          }
        }
      } catch (err) {
        console.log("Fetch reps error:", err);
      }

      // Mark the initial sync as complete so the dashboard renders (or shows the
      // empty-colony state) instead of flashing stale demo content.
      setColoniesLoaded(true);
    };

    loadInitialData();
  }, [isLoggedIn]);

  // Active Colony (null when the backend has no colonies yet — the dashboard
  // renders an empty-charter prompt in that case, see below).
  const currentColony =
    colonies.find((c) => c.id === selectedColonyId) || colonies[0] || null;

  // Active Representative for this colony
  const currentRep =
    representatives.find((r) => r.assigned_colony_id === currentColony?.id) || null;

  // Selected Representative for Representative View
  const selectedRep =
    representatives.find((r) => r.id === selectedRepId) || representatives[0] || null;

  // Filtered collections for active colony
  const colonyInfrastructures = infrastructures.filter(
    (i) => i.colony_id === currentColony?.id
  );
  const colonyUpgrades = upgrades.filter((u) => u.colony_id === currentColony?.id);
  const colonyModifiers = modifiers.filter((m) => m.colony_id === currentColony?.id);
  const colonyResources = resources.filter((r) => r.colony_id === currentColony?.id);
  const colonyPlans = plans.filter((p) => p.colony_id === currentColony?.id);

  // Backend Colony records carry age as `age_days`; the UI renders it as
  // `founding_days`. Normalize on every server round-trip so the displayed
  // age never silently collapses to 0.
  const toColonyWithAge = (c: Colony): Colony => ({
    ...c,
    founding_days: c.founding_days ?? c.age_days ?? 0,
  });

  const handleSetAge = (ageDays: number) => {
    if (!currentColony) return;
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only. Lord Captain or Arch Magos clearance required.");
      return;
    }

    setColonies((prev) =>
      prev.map((c) =>
        c.id === currentColony.id ? { ...c, founding_days: ageDays } : c
      )
    );

    apiFetch(`/api/v1/colonies/${currentColony.id}/age`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ set: ageDays }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((updated) => {
        if (updated?.id) {
          setColonies((prev) =>
            prev.map((c) =>
              c.id === updated.id ? toColonyWithAge(updated) : c
            )
          );
        }
      })
      .catch((err) => console.error("Set age error:", err));
  };

  const handleAdvanceDays = (days: number) => {
    if (!currentColony) return;
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only. Lord Captain or Arch Magos clearance required.");
      return;
    }

    setColonies((prev) =>
      prev.map((c) =>
        c.id === currentColony.id
          ? { ...c, founding_days: (c.founding_days || 0) + days }
          : c
      )
    );

    apiFetch(`/api/v1/colonies/${currentColony.id}/age`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ add: days }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((updated) => {
        if (updated?.id) {
          setColonies((prev) =>
            prev.map((c) =>
              c.id === updated.id ? toColonyWithAge(updated) : c
            )
          );
        }
      })
      .catch((err) => console.error("Advance age error:", err));
  };

  // Reset Seed Data
  const handleResetData = async () => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Resetting canonical database requires Lord Captain or Arch Magos clearance.");
      return;
    }
    try {
      const res = await apiFetch("/api/v1/reset-seed", { method: "POST" });
      if (res.ok) {
        setColonies(INITIAL_COLONIES);
        setRepresentatives(INITIAL_REPRESENTATIVES);
        setInfrastructures(INITIAL_INFRASTRUCTURES);
        setUpgrades(INITIAL_UPGRADES);
        setModifiers(INITIAL_MODIFIERS);
        setResources(INITIAL_RESOURCES);
        setPlans(INITIAL_PLANS);
        setSelectedColonyId(INITIAL_COLONIES[0].id);
        setSelectedRepId(INITIAL_REPRESENTATIVES[0].id);
      }
    } catch (err) {
      console.log("Reset error:", err);
    }
  };

  // Export & Import Database JSON
  const handleExportData = () => {
    const backupData = {
      colonies,
      representatives,
      infrastructures,
      upgrades,
      modifiers,
      resources,
      plans,
    };
    const blob = new Blob([JSON.stringify(backupData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `wh40k_colony_dynasty_records_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportData = async (file: File) => {
    try {
      const parsed = JSON.parse(await file.text());
      if (parsed.colonies) setColonies(parsed.colonies);
      if (parsed.representatives) setRepresentatives(parsed.representatives);
      if (parsed.infrastructures) setInfrastructures(parsed.infrastructures);
      if (parsed.upgrades) setUpgrades(parsed.upgrades);
      if (parsed.modifiers) setModifiers(parsed.modifiers);
      if (parsed.resources) setResources(parsed.resources);
      if (parsed.plans) setPlans(parsed.plans);
    } catch (err) {
      console.error("Invalid import JSON:", err);
    }
  };

  // --- CRUD Handlers ---

  // Colonies
  const handleCreateColony = async (colonyData: any) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only. Lord Captain or Arch Magos clearance required to charter colonies.");
      return;
    }

    // Optimistic local entry so the UI updates immediately. The backend assigns the
    // authoritative integer id; we replace this temporary row once POST resolves so
    // deletes and other operations always target a real colony id (never a synthetic
    // string that the backend would reject with a 422).
    const tempId = `temp-colony-${Date.now()}`;
    const newColony: Colony = {
      id: tempId,
      name: colonyData.name,
      star_system: colonyData.star_system,
      colony_type: colonyData.colony_type,
      base_size: colonyData.base_size || 1,
      base_complacency: colonyData.base_complacency || 0,
      base_order: colonyData.base_order || 0,
      base_productivity: colonyData.base_productivity || 0,
      base_piety: colonyData.base_piety || 0,
      founder_name: colonyData.founder_name,
      founding_days: 0,
      notes: colonyData.notes,
      quote: colonyData.notes,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    setColonies((prev) => [...prev, newColony]);
    setSelectedColonyId(newColony.id);

    try {
      const res = await apiFetch("/api/v1/colonies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newColony),
      });
      if (res.ok) {
        const created = await res.json();
        if (created?.id) {
          // Adopt the backend-assigned id so subsequent operations use a real colony.
          setColonies((prev) => prev.map((c) => (c.id === tempId ? created : c)));
          setSelectedColonyId(created.id);
          fetchColonyDetails(created);
          return created;
        }
      } else {
        console.error("Create colony failed:", res.status);
      }
    } catch (err) {
      console.error("Create colony error:", err);
    }

    // POST failed or returned no id — roll back the optimistic entry.
    setColonies((prev) => prev.filter((c) => c.id !== tempId));
    setSelectedColonyId((prev) => (prev === tempId ? "" : prev));
    return null;
  };

  const handleSaveCharter = (updates: Partial<Colony>) => {
    if (!currentColony) return;
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const updated = { ...currentColony, ...updates };
    setColonies((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));

    apiFetch(`/api/v1/colonies/${updated.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    }).catch(console.error);
  };

  const handleDeleteColony = async (colonyId: string) => {
    if (currentUser?.role !== "admin") {
      alert("Clearance Denied: Arch Magos clearance required to dissolve a colony.");
      return;
    }
    if (!colonyId) return;

    try {
      const res = await apiFetch(`/api/v1/colonies/${colonyId}`, { method: "DELETE" });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        alert(body?.detail || `Failed to delete colony (HTTP ${res.status}).`);
        return;
      }
    } catch (err) {
      console.error("Delete colony error:", err);
      alert("Failed to delete colony. Please check the backend connection and try again.");
      return;
    }

    // Only mutate local state after the server confirms deletion
    setColonies((prev) => prev.filter((c) => c.id !== colonyId));
    setInfrastructures((prev) => prev.filter((i) => i.colony_id !== colonyId));
    setUpgrades((prev) => prev.filter((u) => u.colony_id !== colonyId));
    setModifiers((prev) => prev.filter((m) => m.colony_id !== colonyId));
    setResources((prev) => prev.filter((r) => r.colony_id !== colonyId));
    setPlans((prev) => prev.filter((p) => p.colony_id !== colonyId));
    setSelectedColonyId((prev) => {
      if (prev !== colonyId) return prev;
      // Select the first remaining colony after the deletion (if any).
      return colonies.find((c) => c.id !== colonyId)?.id || "";
    });
  };

  // Representatives
  const handleCommissionRepresentative = (
    repData: Omit<Representative, "id" | "created_at">
  ) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const newRep: Representative = {
      id: `rep-${Date.now()}`,
      ...repData,
      created_at: new Date().toISOString(),
    };

    setRepresentatives((prev) => [...prev, newRep]);
    setSelectedRepId(newRep.id);

    apiFetch("/api/v1/representatives", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newRep),
    }).catch(console.error);
  };

  const handleReassignRepresentative = (repId: string | null) => {
    if (!currentColony) return;
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }

    // Unassign previous rep
    setRepresentatives((prev) =>
      prev.map((r) => {
        if (r.assigned_colony_id === currentColony.id) {
          return { ...r, assigned_colony_id: null };
        }
        if (repId && r.id === repId) {
          return { ...r, assigned_colony_id: currentColony.id };
        }
        return r;
      })
    );

    if (repId) {
      apiFetch(`/api/v1/representatives/${repId}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ colony_id: currentColony.id }),
      }).catch(console.error);
    } else {
      const prevRep = representatives.find((r) => r.assigned_colony_id === currentColony.id);
      if (prevRep) {
        apiFetch(`/api/v1/representatives/${prevRep.id}/assign`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ colony_id: null }),
        }).catch(console.error);
      }
    }
  };

  const syncRepresentativeUpdate = (repId: string, updates: Partial<Representative>) => {
    if (currentUser?.role === "viewer") return;
    apiFetch(`/api/v1/representatives/${repId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    }).catch(console.error);
  };

  const handleUpdateCharacteristics = (
    repId: string,
    charKey: string,
    delta: number
  ) => {
    setRepresentatives((prev) =>
      prev.map((r) => {
        if (r.id === repId && r.characteristics) {
          const currentVal = (r.characteristics as any)[charKey] || 30;
          const updatedChars = {
            ...r.characteristics,
            [charKey]: Math.max(1, Math.min(100, currentVal + delta)),
          };
          syncRepresentativeUpdate(repId, { characteristics: updatedChars });
          return {
            ...r,
            characteristics: updatedChars,
          };
        }
        return r;
      })
    );
  };

  const handleAddSkill = (repId: string, skill: string) => {
    setRepresentatives((prev) =>
      prev.map((r) => {
        if (r.id === repId) {
          const updatedSkills = [...(r.skills || []), skill];
          syncRepresentativeUpdate(repId, { skills: updatedSkills });
          return {
            ...r,
            skills: updatedSkills,
          };
        }
        return r;
      })
    );
  };

  const handleRemoveSkill = (repId: string, skill: string) => {
    setRepresentatives((prev) =>
      prev.map((r) => {
        if (r.id === repId) {
          const updatedSkills = (r.skills || []).filter((s) => s !== skill);
          syncRepresentativeUpdate(repId, { skills: updatedSkills });
          return {
            ...r,
            skills: updatedSkills,
          };
        }
        return r;
      })
    );
  };

  const handleAddTalent = (repId: string, talent: string) => {
    setRepresentatives((prev) =>
      prev.map((r) => {
        if (r.id === repId) {
          const updatedTalents = [...(r.talents || []), talent];
          syncRepresentativeUpdate(repId, { talents: updatedTalents });
          return {
            ...r,
            talents: updatedTalents,
          };
        }
        return r;
      })
    );
  };

  const handleRemoveTalent = (repId: string, talent: string) => {
    setRepresentatives((prev) =>
      prev.map((r) => {
        if (r.id === repId) {
          const updatedTalents = (r.talents || []).filter((t) => t !== talent);
          syncRepresentativeUpdate(repId, { talents: updatedTalents });
          return {
            ...r,
            talents: updatedTalents,
          };
        }
        return r;
      })
    );
  };

  const handleRenameRepresentative = (repId: string, newName: string) => {
    setRepresentatives((prev) =>
      prev.map((r) => (r.id === repId ? { ...r, name: newName } : r))
    );
    syncRepresentativeUpdate(repId, { name: newName });
  };

  // Infrastructure
  const handleCommissionInfrastructure = (
    infraData: Omit<Infrastructure, "id">
  ) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const newInfra: Infrastructure = {
      id: `infra-${Date.now()}`,
      ...infraData,
    };
    setInfrastructures((prev) => [...prev, newInfra]);
    apiFetch(`/api/v1/colonies/${newInfra.colony_id}/infrastructure`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newInfra),
    }).catch(console.error);
  };

  const handleUpdateInfrastructureState = (
    id: string,
    state: Infrastructure["state"]
  ) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = infrastructures.find((i) => i.id === id);
    setInfrastructures((prev) =>
      prev.map((i) => (i.id === id ? { ...i, state } : i))
    );
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/infrastructure/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state }),
      }).catch(console.error);
    }
  };

  const handleDeleteInfrastructure = (id: string) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = infrastructures.find((i) => i.id === id);
    setInfrastructures((prev) => prev.filter((i) => i.id !== id));
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/infrastructure/${id}`, {
        method: "DELETE",
      }).catch(console.error);
    }
  };

  // Support Upgrades
  const handleInstallUpgrade = (upgradeData: Omit<SupportUpgrade, "id">) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const newUpgrade: SupportUpgrade = {
      id: `upg-${Date.now()}`,
      ...upgradeData,
    };
    setUpgrades((prev) => [...prev, newUpgrade]);
    apiFetch(`/api/v1/colonies/${newUpgrade.colony_id}/upgrades`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newUpgrade),
    }).catch(console.error);
  };

  const handleUpdateUpgradeState = (
    id: string,
    state: SupportUpgrade["state"]
  ) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = upgrades.find((u) => u.id === id);
    setUpgrades((prev) => prev.map((u) => (u.id === id ? { ...u, state } : u)));
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/upgrades/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state }),
      }).catch(console.error);
    }
  };

  const handleDeleteUpgrade = (id: string) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = upgrades.find((u) => u.id === id);
    setUpgrades((prev) => prev.filter((u) => u.id !== id));
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/upgrades/${id}`, {
        method: "DELETE",
      }).catch(console.error);
    }
  };

  // Plans & Blueprints
  const handleAddPlan = (planData: Omit<DevelopmentPlan, "id">) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const newPlan: DevelopmentPlan = {
      id: `plan-${Date.now()}`,
      ...planData,
    };
    setPlans((prev) => [...prev, newPlan]);
    apiFetch(`/api/v1/colonies/${newPlan.colony_id}/plans`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newPlan),
    }).catch(console.error);
  };

  const handleDeletePlan = (id: string) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = plans.find((p) => p.id === id);
    setPlans((prev) => prev.filter((p) => p.id !== id));
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/plans/${id}`, {
        method: "DELETE",
      }).catch(console.error);
    }
  };

  const handlePromotePlan = (plan: DevelopmentPlan) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    // If it's a support upgrade, add it to upgrades
    handleInstallUpgrade({
      colony_id: plan.colony_id,
      upgrade_type: (plan.specific_type.toLowerCase().replaceAll(" ", "_") as any) || "garrison",
      name: plan.name,
      state: "working",
      description: plan.description,
      installed_at: new Date().toISOString(),
    });
    // Remove from plans
    handleDeletePlan(plan.id);
  };

  // Modifiers
  const handleAddModifier = (
    modifierData: Omit<Modifier, "id" | "created_at">
  ) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const newMod: Modifier = {
      id: `mod-${Date.now()}`,
      ...modifierData,
      created_at: new Date().toISOString(),
    };
    setModifiers((prev) => [...prev, newMod]);
    apiFetch(`/api/v1/colonies/${newMod.colony_id}/modifiers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newMod),
    }).catch(console.error);
  };

  const handleToggleModifier = (id: string) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = modifiers.find((m) => m.id === id);
    if (!target) return;
    const nextActive = !target.is_active;
    setModifiers((prev) =>
      prev.map((m) => (m.id === id ? { ...m, is_active: nextActive } : m))
    );
    apiFetch(`/api/v1/colonies/${target.colony_id}/modifiers/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_active: nextActive }),
    }).catch(console.error);
  };

  const handleDeleteModifier = (id: string) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = modifiers.find((m) => m.id === id);
    setModifiers((prev) => prev.filter((m) => m.id !== id));
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/modifiers/${id}`, {
        method: "DELETE",
      }).catch(console.error);
    }
  };

  // Resources
  const handleLogResource = (resourceData: Omit<ColonyResource, "id">) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const newRes: ColonyResource = {
      id: `res-${Date.now()}`,
      ...resourceData,
    };
    setResources((prev) => [...prev, newRes]);
    apiFetch(`/api/v1/colonies/${newRes.colony_id}/resources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newRes),
    }).catch(console.error);
  };

  const handleDeleteResource = (id: string) => {
    if (currentUser?.role === "viewer") {
      alert("Clearance Denied: Servitor clearance is read-only.");
      return;
    }
    const target = resources.find((r) => r.id === id);
    setResources((prev) => prev.filter((r) => r.id !== id));
    if (target) {
      apiFetch(`/api/v1/colonies/${target.colony_id}/resources/${id}`, {
        method: "DELETE",
      }).catch(console.error);
    }
  };

  // Show loading state while checking authentication
  if (authLoading) {
    return (
      <div className="min-h-screen bg-[var(--mech-void)] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-[#f59e0b]/30 border-t-[#f59e0b] rounded-full animate-spin mx-auto" />
          <p className="text-[#f59e0b] font-mono-slate text-sm tracking-wider">AUTHENTICATING...</p>
        </div>
      </div>
    );
  }

  // If not logged in, display login screen
  if (!isLoggedIn) {
    return (
      <LoginScreen
        onLogin={(user) => {
          // Populate the session query cache with the just-authenticated user so
          // isLoggedIn flips true and the app transitions to the dashboard without
          // waiting for a full refetch. (LoginScreen calls loginApi directly, so the
          // loginMutation.onSuccess invalidation never runs on this path.)
          queryClient.setQueryData(["auth", "me"], user);
        }}
      />
    );
  }

  // Wait for the initial backend sync so the dashboard doesn't flash an
  // empty/demo state while real colonies are still loading.
  if (!coloniesLoaded) {
    return (
      <div className="min-h-screen bg-[var(--mech-void)] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-[#f59e0b]/30 border-t-[#f59e0b] rounded-full animate-spin mx-auto" />
          <p className="text-[#f59e0b] font-mono-slate text-sm tracking-wider">LOADING IMPERIAL DATASLATE...</p>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    logoutMutation.mutate();
  };

  // No real colonies on the backend yet — the GM is logged in but there is nothing
  // to show. Seed/demo data is not displayed here: it's demo-only and must never be
  // sent to the API, so we prompt to charter the first real colony instead.
  if (!currentColony) {
    return (
      <div
        className="min-h-screen bg-[var(--mech-void)] text-[#f8fafc] flex flex-col justify-between selection:bg-[#f59e0b] selection:text-black"
      >
        <div className="flex-1 flex flex-col">
          <Header
            colonies={colonies}
            selectedColony={currentColony}
            activeTab={activeTab}
            theme={theme}
            opticsSettings={opticsSettings}
            onSelectColony={(colony) => setSelectedColonyId(colony.id)}
            onSelectTab={setActiveTab}
            onAdvanceDays={handleAdvanceDays}
            onOpenNewColony={() => setIsNewColonyOpen(true)}
            onChangeTheme={setTheme}
            onUpdateOpticsSettings={updateOpticsSettings}
            userRole={currentUser?.role || "colony_manager"}
            userName={currentUser?.username || "Alexis Valancius"}
            onLogout={handleLogout}
          />

          <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto flex items-center justify-center">
            <div className="text-center space-y-4">
              <p className="text-[#f59e0b] font-mono-slate text-sm tracking-wider uppercase">
                No colonised worlds on record
              </p>
              <p className="text-[#94a3b8] text-sm max-w-md mx-auto">
                You has not yet registered a colony in the Imperial dataslate.
                Create the first settlement to begin tracking it here.
              </p>
              <button
                onClick={() => setIsNewColonyOpen(true)}
                className="px-5 py-2 rounded font-mono-slate text-sm bg-[#f59e0b]/15 text-[#f59e0b] border border-[#f59e0b]/40 hover:bg-[#f59e0b]/25 transition"
              >
                Found Your First Colony
              </button>
            </div>
          </main>
        </div>

        <Footer
          colonyCount={colonies.length}
          activeColonyName="None"
          onResetSeedData={handleResetData}
          onExportData={handleExportData}
          onImportData={handleImportData}
        />

        <NewColonyModal
          isOpen={isNewColonyOpen}
          onClose={() => setIsNewColonyOpen(false)}
          onCreateColony={handleCreateColony}
        />
      </div>
    );
  }

  // Real-time calculation breakdown (only evaluated once a colony exists — the
  // stubbed calculator dereferences colony fields directly).
  const colonyStats = calculateColonyStats(
    currentColony,
    currentRep ? [currentRep] : [],
    colonyInfrastructures,
    colonyUpgrades,
    colonyModifiers
  );

  return (
    <div
      className="min-h-screen bg-[var(--mech-void)] text-[#f8fafc] flex flex-col justify-between selection:bg-[#f59e0b] selection:text-black"
    >
      {/* Optional CRT scanline / flicker effect */}
      {opticsSettings.crt_flicker && (
        <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.4)_100%)] z-40 opacity-70" />
      )}

      {/* Main Container */}
      <div className="flex-1 flex flex-col">
        {/* 1. Global Header */}
        <Header
          colonies={colonies}
          selectedColony={currentColony}
          activeTab={activeTab}
          theme={theme}
          opticsSettings={opticsSettings}
          onSelectColony={(colony) => setSelectedColonyId(colony.id)}
          onSelectTab={setActiveTab}
          onAdvanceDays={handleAdvanceDays}
          onOpenNewColony={() => {
            if (currentUser?.role === "viewer") {
              alert("Clearance Denied: Servitor clearance is read-only. Lord Captain or Arch Magos clearance required.");
              return;
            }
            setIsNewColonyOpen(true);
          }}
          onChangeTheme={setTheme}
          onUpdateOpticsSettings={updateOpticsSettings}
          userRole={currentUser?.role || "colony_manager"}
          userName={currentUser?.username || "Alexis Valancius"}
          onLogout={handleLogout}
        />

        {/* 2. Main Tab Viewports */}
        <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto">
          {activeTab === "overview" && (
            <ColonyOverview
              colony={currentColony}
              stats={colonyStats}
              representative={currentRep}
              infrastructures={colonyInfrastructures}
              upgrades={colonyUpgrades}
              resources={colonyResources}
              onNavigateTab={(tab) => setActiveTab(tab)}
            />
          )}

          {activeTab === "details" && (
            <ColonyDetailsView
              colony={currentColony}
              stats={colonyStats}
              modifiers={colonyModifiers}
              resources={colonyResources}
              representative={currentRep}
              onAdvanceDays={handleAdvanceDays}
              onSetAge={handleSetAge}
              onOpenEditCharter={() => setIsEditCharterOpen(true)}
              onOpenAddModifier={() => setIsAddModifierOpen(true)}
              onOpenLogResource={() => setIsLogResourceOpen(true)}
              onToggleModifier={handleToggleModifier}
              onDeleteModifier={handleDeleteModifier}
              onDeleteResource={handleDeleteResource}
              canDelete={currentUser?.role === "admin"}
              onDeleteColony={() => handleDeleteColony(currentColony.id)}
            />
          )}

          {activeTab === "infrastructure" && (
            <InfrastructurePlansView
              stats={colonyStats}
              infrastructures={colonyInfrastructures}
              upgrades={colonyUpgrades}
              plans={colonyPlans}
              onOpenCommissionSystem={() => setIsCommissionSystemOpen(true)}
              onOpenInstallUpgrade={() => setIsInstallUpgradeOpen(true)}
              onOpenAddBlueprint={() => setIsAddBlueprintOpen(true)}
              onUpdateInfrastructureState={handleUpdateInfrastructureState}
              onUpdateUpgradeState={handleUpdateUpgradeState}
              onDeleteInfrastructure={handleDeleteInfrastructure}
              onDeleteUpgrade={handleDeleteUpgrade}
              onDeletePlan={handleDeletePlan}
              onPromotePlan={handlePromotePlan}
            />
          )}

          {activeTab === "representatives" && (
            <RepresentativeView
              representatives={representatives}
              selectedRepresentative={selectedRep}
              colonies={colonies}
              onSelectRepresentative={(rep) => setSelectedRepId(rep.id)}
              onOpenCommissionModal={() => setIsCommissionRepOpen(true)}
              onOpenReassignModal={(rep) => {
                setSelectedRepId(rep.id);
                setIsReassignRepOpen(true);
              }}
              onUpdateCharacteristics={handleUpdateCharacteristics}
              onAddSkill={handleAddSkill}
              onRemoveSkill={handleRemoveSkill}
              onAddTalent={handleAddTalent}
              onRemoveTalent={handleRemoveTalent}
              onRenameRepresentative={handleRenameRepresentative}
            />
          )}
        </main>
      </div>

      {/* 3. Global Footer */}
      <Footer
        colonyCount={colonies.length}
        activeColonyName={currentColony?.name || "None"}
        onResetSeedData={handleResetData}
        onExportData={handleExportData}
        onImportData={handleImportData}
      />

      {/* 4. Modals */}
      <NewColonyModal
        isOpen={isNewColonyOpen}
        onClose={() => setIsNewColonyOpen(false)}
        onCreateColony={handleCreateColony}
      />

      <CommissionRepresentativeModal
        isOpen={isCommissionRepOpen}
        onClose={() => setIsCommissionRepOpen(false)}
        colonies={colonies}
        onCommission={handleCommissionRepresentative}
      />

      <ReassignRepresentativeModal
        isOpen={isReassignRepOpen}
        onClose={() => setIsReassignRepOpen(false)}
        colony={currentColony}
        representatives={representatives}
        currentRepresentative={currentRep}
        onReassign={handleReassignRepresentative}
      />

      <CommissionHardInfrastructureModal
        isOpen={isCommissionSystemOpen}
        onClose={() => setIsCommissionSystemOpen(false)}
        colonyId={currentColony?.id || ""}
        onCommission={handleCommissionInfrastructure}
      />

      <AddSupportUpgradeModal
        isOpen={isInstallUpgradeOpen}
        onClose={() => setIsInstallUpgradeOpen(false)}
        colonyId={currentColony?.id || ""}
        onInstall={handleInstallUpgrade}
      />

      <AddBlueprintModal
        isOpen={isAddBlueprintOpen}
        onClose={() => setIsAddBlueprintOpen(false)}
        colonyId={currentColony?.id || ""}
        onAddPlan={handleAddPlan}
      />

      <AddCustomModifierModal
        isOpen={isAddModifierOpen}
        onClose={() => setIsAddModifierOpen(false)}
        colonyId={currentColony?.id || ""}
        onAddModifier={handleAddModifier}
      />

      <LogResourceDepositModal
        isOpen={isLogResourceOpen}
        onClose={() => setIsLogResourceOpen(false)}
        colonyId={currentColony?.id || ""}
        onLogResource={handleLogResource}
      />

      {currentColony && (
        <EditCharterModal
          isOpen={isEditCharterOpen}
          onClose={() => setIsEditCharterOpen(false)}
          colony={currentColony}
          onSaveCharter={handleSaveCharter}
        />
      )}
    </div>
  );
}

export default App;
