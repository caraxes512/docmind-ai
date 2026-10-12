"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { useUpdateProfile } from "@/hooks/use-auth-mutations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export default function ProfilePage() {
  const { user } = useAuth();
  const updateProfile = useUpdateProfile();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [saved, setSaved] = useState(false);

  const initials = (user?.full_name || user?.email || "?")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaved(false);
    await updateProfile.mutateAsync(fullName);
    setSaved(true);
  };

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <h1 className="mb-8 font-display text-2xl font-medium text-paper">Profile</h1>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Avatar className="h-14 w-14">
              <AvatarFallback className="text-lg">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <CardTitle>{user.full_name || "Unnamed"}</CardTitle>
              <CardDescription>{user.email}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="full-name">Full name</Label>
              <Input id="full-name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Email</Label>
              <Input value={user.email} disabled />
              <p className="text-xs text-paper-dim">Email changes aren&apos;t supported yet.</p>
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={updateProfile.isPending}>
                {updateProfile.isPending ? "Saving…" : "Save changes"}
              </Button>
              {saved && <span className="text-sm text-success">Saved</span>}
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
