"""Sample parameters and checks for interview_scheduler.py requirements."""

from datetime import datetime

from interview_scheduler import PANEL_SIZE, InterviewScheduler


START = datetime(2026, 11, 9, 9, 0)
END = datetime(2026, 11, 9, 12, 0)
INTERVIEW_START = datetime(2026, 11, 9, 10, 0)


def add_interviewer_availability(
    scheduler: InterviewScheduler, *interviewer_ids: str
) -> None:
    for interviewer_id in interviewer_ids:
        scheduler.add_availability(interviewer_id, START, END)


def verify_available_slots() -> None:
    scheduler = InterviewScheduler()
    add_interviewer_availability(scheduler, "cameron", "peter")

    slots = scheduler.available_slots("candidate-1")

    expected_slots = [
        datetime(2026, 11, 9, 9, 0),
        datetime(2026, 11, 9, 9, 30),
        datetime(2026, 11, 9, 10, 0),
        datetime(2026, 11, 9, 10, 30),
        datetime(2026, 11, 9, 11, 0),
    ]
    assert slots == expected_slots
    print("1. Available slots calculated:", slots)


def verify_conflict_of_interest_recusal() -> None:
    scheduler = InterviewScheduler()
    add_interviewer_availability(scheduler, "cameron", "peter", "edwin")
    scheduler.interviewers["peter"].recused_from.add("candidate-2")

    interview = scheduler.book("candidate-2", INTERVIEW_START)

    assert "peter" not in interview.interviewer_ids
    assert len(interview.interviewer_ids) == PANEL_SIZE
    print("2. Recusal honored:", interview.interviewer_ids)


def verify_two_interviewers_and_slot_capacity() -> None:
    scheduler = InterviewScheduler()
    add_interviewer_availability(
        scheduler, "cameron", "edwin", "peter", "interviewer1"
    )

    first = scheduler.book("candidate-3", INTERVIEW_START)
    second = scheduler.book("candidate-4", INTERVIEW_START)

    assert len(first.interviewer_ids) == PANEL_SIZE
    assert len(second.interviewer_ids) == PANEL_SIZE
    assert set(first.interviewer_ids).isdisjoint(second.interviewer_ids)
    assert first.start == second.start

    try:
        scheduler.book("candidate-5", INTERVIEW_START)
    except ValueError:
        pass
    else:
        raise AssertionError("A third interview should exceed four-interviewer capacity")

    print("3. Two-person panels share capacity:", first.interviewer_ids, second.interviewer_ids)


if __name__ == "__main__":
    verify_available_slots()
    verify_conflict_of_interest_recusal()
    verify_two_interviewers_and_slot_capacity()
    print("All scheduling requirements passed.")
