"use client"
import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { AlertTriangle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { clearAuthState, deleteMeApi, updateMeApi, type Me } from "@/services/auth"

const NAME_MAX_LENGTH = 100
/** Typed verbatim to arm the confirm button — no single click can delete. */
const CONFIRM_PHRASE = "DELETE"

/** Mirrors the backend rules so the user sees the problem before a round trip. */
function validateName(value: string): string | undefined {
  const trimmed = value.trim()
  if (!trimmed) return "Name is required"
  if (trimmed.length < 2) return "Name must be at least 2 characters"
  if (trimmed.length > NAME_MAX_LENGTH) return `Name must be ${NAME_MAX_LENGTH} characters or less`
  return undefined
}

interface DeleteAccountDialogProps {
  isOpen: boolean
  email: string
  onClose: () => void
}

function DeleteAccountDialog({ isOpen, email, onClose }: DeleteAccountDialogProps) {
  const router = useRouter()
  const [confirmation, setConfirmation] = React.useState("")
  const [isDeleting, setIsDeleting] = React.useState(false)
  const [error, setError] = React.useState<string | undefined>()

  const isArmed = confirmation.trim() === CONFIRM_PHRASE

  const handleOpenChange = (open: boolean) => {
    // Closing mid-request would strand the user on a dashboard that is about
    // to stop existing, so the dialog stays put until the call settles.
    if (open || isDeleting) return
    setConfirmation("")
    setError(undefined)
    onClose()
  }

  const handleDelete = async () => {
    if (!isArmed || isDeleting) return
    setIsDeleting(true)
    setError(undefined)
    try {
      await deleteMeApi()
      clearAuthState()
      router.replace("/login?deleted=1")
    } catch (err: unknown) {
      // The account still exists — say so inline and leave the dialog open.
      setError(err instanceof Error ? err.message : "Failed to delete account")
      setIsDeleting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogContent
        className="max-w-md"
        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A", color: "#F5F5F5" }}
      >
        <DialogHeader>
          <div className="mb-1 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" style={{ color: "#F87171" }} aria-hidden />
            <DialogTitle style={{ color: "#F5F5F5" }}>Delete your account?</DialogTitle>
          </div>
          <DialogDescription style={{ color: "#888888" }}>
            This permanently deletes <span style={{ color: "#F5F5F5" }}>{email}</span> along with
            every post, media upload, brand voice and AI memory on it. This cannot be undone, and
            there is no way to recover the data afterwards.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <label htmlFor="delete-confirm" className="block text-xs font-medium" style={{ color: "#F5F5F5" }}>
            Type <span style={{ color: "#F87171" }}>{CONFIRM_PHRASE}</span> to confirm
          </label>
          <input
            id="delete-confirm"
            type="text"
            value={confirmation}
            onChange={(e) => setConfirmation(e.target.value)}
            disabled={isDeleting}
            autoComplete="off"
            spellCheck={false}
            placeholder={CONFIRM_PHRASE}
            aria-describedby={error ? "delete-account-error" : undefined}
            className="w-full rounded-lg border px-3 py-2 text-sm outline-none placeholder:text-[#555555] focus:border-[#F87171] disabled:opacity-60"
            style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#F5F5F5" }}
          />
          {error && (
            <p id="delete-account-error" className="text-xs" style={{ color: "#F87171" }} role="alert">
              {error}
            </p>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => handleOpenChange(false)}
            disabled={isDeleting}
            className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:border-[#444444] hover:text-[#F5F5F5] disabled:cursor-not-allowed disabled:opacity-40"
            style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={!isArmed || isDeleting}
            className="rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            style={{ backgroundColor: "#DC2626", color: "#F5F5F5" }}
          >
            {isDeleting ? "Deleting…" : "Permanently delete account"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

interface AccountSettingsProps {
  me: Me | null
  isLoading: boolean
  /** Applies the new profile locally so the dashboard greeting updates with it. */
  onMeChange: (me: Me) => void
  onToast: (message: string, type: "success" | "error") => void
}

export function AccountSettings({ me, isLoading, onMeChange, onToast }: AccountSettingsProps) {
  const savedName = me?.name ?? ""
  const [name, setName] = React.useState(savedName)
  const [syncedName, setSyncedName] = React.useState(savedName)
  const [touched, setTouched] = React.useState(false)
  const [isSaving, setIsSaving] = React.useState(false)
  const [isDeleteOpen, setIsDeleteOpen] = React.useState(false)

  // Reseed the input when the profile arrives or changes underneath us. Done
  // during render (React's "adjusting state on prop change" pattern) rather
  // than in an effect, which would cost an extra render pass.
  if (savedName !== syncedName) {
    setSyncedName(savedName)
    setName(savedName)
    setTouched(false)
  }

  const nameError = validateName(name)
  const showNameError = touched && nameError
  const isDirty = name.trim() !== savedName

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!me) return
    if (nameError) {
      setTouched(true)
      return
    }

    const trimmed = name.trim()
    const previous = me
    // Optimistic: show the new name immediately, roll back if the PATCH fails.
    onMeChange({ ...me, name: trimmed })
    setIsSaving(true)
    try {
      const updated = await updateMeApi({ name: trimmed })
      onMeChange(updated)
      onToast("Name updated ✓", "success")
    } catch (err: unknown) {
      // Rolling back the profile also reseeds the input via the sync above.
      onMeChange(previous)
      onToast(err instanceof Error ? err.message : "Failed to update name", "error")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <>
      <div
        className="rounded-lg border p-4"
        style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
      >
        <p className="mb-0.5 text-sm font-medium" style={{ color: "#F5F5F5" }}>Account</p>
        <p className="mb-4 text-xs" style={{ color: "#888888" }}>
          Your profile details.
        </p>

        {isLoading ? (
          <p className="text-sm" style={{ color: "#888888" }}>Loading…</p>
        ) : !me ? (
          <p className="text-sm" style={{ color: "#888888" }}>
            Couldn&apos;t load your profile. Refresh to try again.
          </p>
        ) : (
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-1.5">
              <label htmlFor="account-name" className="block text-xs font-medium" style={{ color: "#F5F5F5" }}>
                Name
              </label>
              <input
                id="account-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => setTouched(true)}
                maxLength={NAME_MAX_LENGTH}
                disabled={isSaving}
                placeholder="Add your name"
                aria-invalid={showNameError ? true : undefined}
                aria-describedby={showNameError ? "account-name-error" : undefined}
                className="w-full rounded-lg border px-3 py-2 text-sm outline-none placeholder:text-[#555555] focus:border-[#E1306C] disabled:opacity-60"
                style={{
                  backgroundColor: "#0F0F0F",
                  borderColor: showNameError ? "#E1306C" : "#2A2A2A",
                  color: "#F5F5F5",
                }}
              />
              {showNameError && (
                <p id="account-name-error" className="text-xs" style={{ color: "#E1306C" }}>
                  {nameError}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label htmlFor="account-email" className="block text-xs font-medium" style={{ color: "#F5F5F5" }}>
                Email
              </label>
              <input
                id="account-email"
                type="email"
                value={me.email}
                readOnly
                disabled
                className="w-full cursor-not-allowed rounded-lg border px-3 py-2 text-sm outline-none"
                style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#888888" }}
              />
              <p className="text-xs" style={{ color: "#555555" }}>
                Email can&apos;t be changed yet.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              <button
                type="submit"
                disabled={isSaving || !isDirty || !!nameError}
                className="rounded-lg px-4 py-2 text-sm font-medium transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
              >
                {isSaving ? "Saving…" : "Save changes"}
              </button>
              <Link
                href="/forgot-password"
                className="text-xs underline-offset-4 hover:underline"
                style={{ color: "#888888" }}
              >
                Reset your password
              </Link>
            </div>
          </form>
        )}
      </div>

      {me && (
        <>
          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: "#1A1A1A", borderColor: "#4A1F1F" }}
          >
            <p className="mb-0.5 text-sm font-medium" style={{ color: "#F87171" }}>Danger zone</p>
            <p className="mb-3 text-xs" style={{ color: "#888888" }}>
              Deleting your account erases your posts, media, brand voice and AI memory for good.
              There is no undo and no way to get the data back.
            </p>
            <button
              type="button"
              onClick={() => setIsDeleteOpen(true)}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-[#DC2626] hover:text-[#F5F5F5]"
              style={{ backgroundColor: "transparent", borderColor: "#DC2626", color: "#F87171" }}
            >
              Delete account
            </button>
          </div>

          <DeleteAccountDialog
            isOpen={isDeleteOpen}
            email={me.email}
            onClose={() => setIsDeleteOpen(false)}
          />
        </>
      )}
    </>
  )
}
