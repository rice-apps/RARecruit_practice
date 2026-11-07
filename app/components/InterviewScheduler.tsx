"use client";
import { useMemo, useState } from "react";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Placeholder data: replace with a fetch to your backend later
function getAvailableSlots(date: Date): string[] {
  const day = date.getDay();
  if (day === 0 || day === 6) return []; // no weekends
  return ["9:00 AM", "10:00 AM", "11:30 AM", "1:00 PM", "2:30 PM", "4:00 PM"];
}

export default function InterviewScheduler() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const [viewMonth, setViewMonth] = useState(
    new Date(today.getFullYear(), today.getMonth(), 1)
  );
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);

  const cells = useMemo(() => {
    const year = viewMonth.getFullYear();
    const month = viewMonth.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const arr: (Date | null)[] = Array(firstDay).fill(null);
    for (let d = 1; d <= daysInMonth; d++) arr.push(new Date(year, month, d));
    return arr;
  }, [viewMonth]);

  const slots = selectedDate ? getAvailableSlots(selectedDate) : [];

  const changeMonth = (offset: number) =>
    setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + offset, 1));

  const isPrevDisabled =
    viewMonth.getFullYear() === today.getFullYear() &&
    viewMonth.getMonth() === today.getMonth();

  if (confirmed && selectedDate && selectedTime) {
    return (
      <section className="mx-auto my-8 max-w-3xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="py-8 text-center">
          <h2 className="text-2xl font-semibold text-gray-900">Interview scheduled!</h2>
          <p className="mt-2 text-gray-600">
            {selectedDate.toLocaleDateString(undefined, {
              weekday: "long", month: "long", day: "numeric",
            })}{" "}
            at <span className="font-medium text-gray-900">{selectedTime}</span>
          </p>
          <button
            onClick={() => { setConfirmed(false); setSelectedTime(null); }}
            className="mt-6 rounded-lg border border-indigo-600 px-5 py-2 font-semibold text-indigo-600 hover:bg-indigo-50"
          >
            Reschedule
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto my-8 max-w-3xl rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="text-2xl font-semibold text-gray-900">Schedule Your Interview</h2>
      <p className="mb-6 mt-1 text-gray-500">Pick a date and time that works for you.</p>

      <div className="grid gap-6 md:grid-cols-[1fr_240px]">
        {/* Calendar */}
        <div>
          <div className="mb-3 flex items-center justify-between font-semibold text-gray-900">
            <button
              onClick={() => changeMonth(-1)}
              disabled={isPrevDisabled}
              aria-label="Previous month"
              className="rounded-full px-3 py-1 text-xl hover:bg-gray-100 disabled:cursor-default disabled:opacity-30 disabled:hover:bg-transparent"
            >
              ‹
            </button>
            <span>
              {viewMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" })}
            </span>
            <button
              onClick={() => changeMonth(1)}
              aria-label="Next month"
              className="rounded-full px-3 py-1 text-xl hover:bg-gray-100"
            >
              ›
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1">
            {DAYS.map((d) => (
              <div key={d} className="py-1 text-center text-xs text-gray-400">{d}</div>
            ))}
            {cells.map((date, i) => {
              if (!date) return <div key={i} />;
              const disabled = date < today || getAvailableSlots(date).length === 0;
              const selected = selectedDate?.toDateString() === date.toDateString();
              return (
                <button
                  key={i}
                  disabled={disabled}
                  onClick={() => { setSelectedDate(date); setSelectedTime(null); }}
                  className={`aspect-square rounded-full text-sm transition-colors
                    ${selected
                      ? "bg-indigo-600 font-semibold text-white"
                      : disabled
                        ? "cursor-default text-gray-300"
                        : "bg-indigo-50 font-semibold text-indigo-700 hover:bg-indigo-200"}`}
                >
                  {date.getDate()}
                </button>
              );
            })}
          </div>
        </div>

        {/* Time slots */}
        <div>
          {!selectedDate ? (
            <p className="text-gray-400">Select a date to see available times.</p>
          ) : (
            <>
              <h3 className="mb-3 font-semibold text-gray-900">
                {selectedDate.toLocaleDateString(undefined, {
                  weekday: "long", month: "short", day: "numeric",
                })}
              </h3>
              <div className="mb-4 flex max-h-72 flex-col gap-2 overflow-y-auto">
                {slots.map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedTime(t)}
                    className={`rounded-lg border border-indigo-600 py-2.5 font-semibold transition-colors
                      ${selectedTime === t
                        ? "bg-indigo-600 text-white"
                        : "bg-white text-indigo-600 hover:bg-indigo-50"}`}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <button
                disabled={!selectedTime}
                onClick={() => setConfirmed(true)}
                className="w-full rounded-lg bg-indigo-600 py-3 font-semibold text-white hover:bg-indigo-700 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-indigo-600"
              >
                Confirm Interview
              </button>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
