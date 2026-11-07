import Link from "next/link";

const links = [
  { href: "/interviewer", label: "Home" },
  { href: "/interviewer/availability", label: "Availability" },
  { href: "/interviewer/applications", label: "Applications" },
  { href: "/interviewer/candidates", label: "Candidates" },
  { href: "/interviewer/interviews", label: "Interviews" },
];

export default function InterviewerLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <nav className="flex gap-6 border-b px-8 py-4">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className="hover:underline">
            {l.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
