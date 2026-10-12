import Link from "next/link";
import { ArrowRight, FileText, GitBranch, MessageSquare, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BlueprintHero } from "@/components/blueprint-hero";

const FEATURES = [
  {
    icon: FileText,
    title: "Full documentation, not summaries",
    description:
      "READMEs, API references, architecture docs, and diagrams — generated from real static analysis of your codebase, not a single prompt over a file list.",
  },
  {
    icon: MessageSquare,
    title: "Ask your repository questions",
    description:
      '"Where is JWT implemented?" "How does payment work?" Get answers grounded in your actual source, with file-level citations.',
  },
  {
    icon: RefreshCw,
    title: "Incremental, not wasteful",
    description:
      "Change one file and only the affected documentation regenerates — not the entire repository, every time.",
  },
  {
    icon: GitBranch,
    title: "Reviewed before you trust it",
    description:
      "An AI reviewer checks every generated document for missing sections, broken links, and outdated APIs, and scores it.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-blueprint-canvas">
      <header className="border-b border-ink-700">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="font-display text-lg font-semibold text-paper">DocMind AI</span>
          <nav className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link href="/login">Log in</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Get started</Link>
            </Button>
          </nav>
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 py-20 lg:grid-cols-2">
        <div>
          <h1 className="font-display text-4xl font-medium leading-tight text-paper sm:text-5xl">
            Your codebase&apos;s blueprint,
            <br />
            <span className="text-blueprint">drawn and annotated</span> by AI.
          </h1>
          <p className="mt-6 max-w-md text-base text-paper-dim">
            DocMind AI reads your entire repository — structure, dependencies, APIs, database
            models — and produces documentation that&apos;s accurate, current, and something your
            team will actually trust.
          </p>
          <div className="mt-8 flex items-center gap-4">
            <Button size="lg" asChild>
              <Link href="/register">
                Start documenting <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/login">Log in</Link>
            </Button>
          </div>
        </div>
        <div className="flex justify-center">
          <BlueprintHero />
        </div>
      </section>

      <section className="border-t border-ink-700 bg-ink-900/60">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="font-display text-2xl font-medium text-paper">
            Understands your codebase. Doesn&apos;t guess at it.
          </h2>
          <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
            {FEATURES.map((feature) => (
              <Card key={feature.title}>
                <CardHeader>
                  <feature.icon className="mb-2 h-5 w-5 text-annotation" />
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-ink-700 px-6 py-8 text-center text-sm text-paper-dim">
        DocMind AI — open-source AI documentation generation.
      </footer>
    </div>
  );
}
