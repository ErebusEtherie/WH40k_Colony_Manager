import React, { useState } from "react";
import { Colony } from "../../types/colony";
import { X, Edit3 } from "lucide-react";

interface EditCharterModalProps {
  isOpen: boolean;
  onClose: () => void;
  colony: Colony;
  onSaveCharter: (updates: Partial<Colony>) => void;
}

export const EditCharterModal: React.FC<EditCharterModalProps> = ({
  isOpen,
  onClose,
  colony,
  onSaveCharter,
}) => {
  const [name, setName] = useState(colony.name);
  const [starSystem, setStarSystem] = useState(colony.star_system ?? "");
  const [founderName, setFounderName] = useState(colony.founder_name ?? "");
  const [notes, setNotes] = useState(colony.notes ?? "");

  if (!isOpen) return null;

  const handleSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    onSaveCharter({
      name: name.trim() || colony.name,
      star_system: starSystem.trim(),
      founder_name: founderName.trim(),
      notes: notes.trim(),
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="gothic-bracket-box w-full max-w-lg bg-[#0a0e18] border border-[#f59e0b]/60 rounded-lg shadow-2xl p-6 relative">
        <div className="gothic-bracket-bottom-left" />
        <div className="gothic-bracket-bottom-right" />

        <div className="flex items-center justify-between border-b border-[#222e46] pb-3 mb-4">
          <div className="flex items-center space-x-2">
            <Edit3 className="w-5 h-5 text-[#f59e0b]" />
            <div>
              <h2 className="font-gothic font-bold text-base tracking-wider text-[#fef08a] uppercase">
                EDIT COLONY CHARTER DOSSIER
              </h2>
              <p className="text-xs text-[#94a3b8] font-mono-slate">
                Update administrative designation and records
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#64748b] hover:text-white p-1 rounded transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 font-mono-slate text-xs">
          <div>
            <label
              htmlFor="edit-charter-name"
              className="block text-[#cbd5e1] uppercase tracking-wider mb-1 font-semibold"
            >
              Colony Name
            </label>
            <input
              id="edit-charter-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#070a12] border border-[#252f44] focus:border-[#f59e0b] text-[#f8fafc] px-3 py-2 rounded focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="edit-charter-system"
                className="block text-[#cbd5e1] uppercase tracking-wider mb-1 font-semibold"
              >
                Star System
              </label>
              <input
                id="edit-charter-system"
                type="text"
                value={starSystem}
                onChange={(e) => setStarSystem(e.target.value)}
                placeholder="Uncharted System"
                className="w-full bg-[#070a12] border border-[#252f44] focus:border-[#f59e0b] text-[#f8fafc] px-3 py-2 rounded focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="edit-charter-founder"
                className="block text-[#cbd5e1] uppercase tracking-wider mb-1 font-semibold"
              >
                Founder *
              </label>
              <input
                id="edit-charter-founder"
                type="text"
                value={founderName}
                onChange={(e) => setFounderName(e.target.value)}
                className="w-full bg-[#070a12] border border-[#252f44] focus:border-[#f59e0b] text-[#f8fafc] px-3 py-2 rounded focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="edit-charter-notes"
              className="block text-[#cbd5e1] uppercase tracking-wider mb-1 font-semibold"
            >
              Colony Dossier Notes & Strategic Intent
            </label>
            <textarea
              id="edit-charter-notes"
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-[#070a12] border border-[#252f44] focus:border-[#f59e0b] text-[#f8fafc] px-3 py-2 rounded focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-[#222e46]">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-[#121828] hover:bg-[#1a233a] border border-[#2c364d] text-xs text-[#94a3b8] hover:text-white rounded uppercase font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 bg-gradient-to-r from-[#b45309] to-[#f59e0b] hover:from-[#d97706] hover:to-[#fcd34d] text-[#06080e] font-gothic font-bold text-xs uppercase tracking-wider rounded transition shadow-lg"
            >
              Save Charter
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
