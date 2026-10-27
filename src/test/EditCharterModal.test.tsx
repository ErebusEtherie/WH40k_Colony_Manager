import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EditCharterModal } from "../components/modals/EditCharterModal";
import type { Colony } from "../types/colony";

const colony: Colony = {
  id: "1",
  name: "Dargonus Prime",
  colony_type: "mining_and_industry",
  base_complacency: 1,
  base_order: 2,
  base_productivity: 3,
  base_piety: 1,
  base_size: 1,
  founder_name: "Von Valancius Dynasty",
  star_system: "Koronus Expanse",
  notes: "Primary administrative seat.",
  created_at: "2023-01-10T08:00:00Z",
  updated_at: "2023-01-10T08:00:00Z",
};

describe("EditCharterModal dossier notes", () => {
  it("pre-fills the dossier notes field with the colony's notes", () => {
    render(
      <EditCharterModal isOpen onClose={vi.fn()} colony={colony} onSaveCharter={vi.fn()} />
    );
    const textarea = screen.getByLabelText(
      "Colony Dossier Notes & Strategic Intent"
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe("Primary administrative seat.");
  });

  it("submits the edited notes alongside the charter fields", () => {
    const onSaveCharter = vi.fn();
    const onClose = vi.fn();
    render(
      <EditCharterModal isOpen onClose={onClose} colony={colony} onSaveCharter={onSaveCharter} />
    );

    const textarea = screen.getByLabelText(
      "Colony Dossier Notes & Strategic Intent"
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Updated strategic intent." } });
    fireEvent.click(screen.getByRole("button", { name: /save charter/i }));

    expect(onSaveCharter).toHaveBeenCalledWith(
      expect.objectContaining({ notes: "Updated strategic intent." })
    );
    expect(onClose).toHaveBeenCalled();
  });
});
