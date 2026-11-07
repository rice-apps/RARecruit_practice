import Link from "next/link";

// mock data for upcoming interviews
const upcoming = [
  { id: "1", candidate: "Jane Doe", time: "Nov 10, 2:00 PM" },
  { id: "2", candidate: "John Smith", time: "Nov 11, 10:30 AM" },
];

export default function InterviewerHome() {
  return (
    <main className="p-8 space-y-8">
      <h1 className="text-3xl font-bold">Interviewer</h1>

      <div className="flex gap-3">
        <Link href="/interviewer/availability" className="rounded-md bg-black px-4 py-2 text-white hover:bg-gray-800">
          Edit Availability
        </Link>
        <Link href="/interviewer/applications" className="rounded-md border px-4 py-2 hover:bg-gray-100">
          Continue Grading
        </Link>
        <Link href="/interviewer/candidates" className="rounded-md border px-4 py-2 hover:bg-gray-100">
          View Candidates
        </Link>
      </div>

      <section>
        <h2 className="mb-3 text-xl font-semibold">Upcoming Interviews</h2>
        <ul className="divide-y rounded-md border">
          {upcoming.map((i) => (
            <li key={i.id}>
              <Link href={`/interviewer/interviews/${i.id}`} className="flex justify-between p-3 hover:bg-gray-50">
                <span>{i.candidate}</span>
                <span className="text-gray-500">{i.time}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}