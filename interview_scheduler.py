from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock
from typing import Callable

# constants: each interview lasts 60 minutes, possible start times generated every 30 minutes, each interview requires 2 interviewers
PANEL_SIZE = 2
SLOT_LENGTH = timedelta(minutes=60)
SLOT_STEP = timedelta(minutes=30)

@dataclass
#interviewer stores identifier, availability windows, and candidates they can't interview
class Interviewer:
    id: str
    availability: list = field(default_factory=list)
    recused_from: set = field(default_factory=set)

@dataclass
#interview stores canddidate identifier, start time, assigned interviewer ids
class Interview:
    candidate_id: str
    start: datetime
    interviewer_ids: list


class InterviewScheduler:
    def __init__(self):
        self.interviewers = {}
        self.interviews = []
        self._lock = RLock()
        self._subscribers: list[Callable[[str, Interview], None]] = []


#new availabiility windows are added to the interviewer's list of availability, with validation that start is before end
    def add_availability(self, interviewer_id, start, end):
        if start >= end:
            raise ValueError("Availability must start before it ends")
        iv = self.interviewers.setdefault(interviewer_id, Interviewer(interviewer_id))
        iv.availability.append((start, end))

    def set_availability(self, interviewer_id, windows):
        validated = list(windows)
        if any(start >= end for start, end in validated):
            raise ValueError("Availability must start before it ends")
        iv = self.interviewers.setdefault(interviewer_id, Interviewer(interviewer_id))
        iv.availability = validated

    def remove_availability(self, interviewer_id, start, end):
        iv = self._get_interviewer(interviewer_id)
        try:
            iv.availability.remove((start, end))
        except ValueError as exc:
            raise ValueError("Availability window was not found") from exc


# add person to interviewer's recusal list, remove person from recusal list, and get interviewer object by id with error handling
    def add_conflict(self, interviewer_id, candidate_id):
        self._get_interviewer(interviewer_id).recused_from.add(candidate_id)

    def remove_conflict(self, interviewer_id, candidate_id):
        self._get_interviewer(interviewer_id).recused_from.discard(candidate_id)

    def _get_interviewer(self, interviewer_id):
        try:
            return self.interviewers[interviewer_id]
        except KeyError as exc:
            raise ValueError(f"Unknown interviewer: {interviewer_id}") from exc

    #convert availability windows into potential one hour start times (i.e. availability from 9 to 11 generates 9:00, 9:30, 10:00)
    def slots_for(self, iv: Interviewer):
        starts = set()
        for win_start, win_end in iv.availability:
            t = win_start
            while t + SLOT_LENGTH <= win_end:
                starts.add(t)
                t += SLOT_STEP
        return starts
    
    #check if an interviewer is already booked for a given start time
    def _is_booked(self, interviewer_id, start):
        end = start + SLOT_LENGTH
        return any(
            interviewer_id in i.interviewer_ids and start < i.start + SLOT_LENGTH and i.start < end
            for i in self.interviews
        )

    #filter interviewers who are available at the time, haven't recused themselves, and aren't assigned to overlapping interview
    def eligible_interviewers(self, candidate_id, start):
        return [
            iv for iv in self.interviewers.values()
            if start in self.slots_for(iv)
            and candidate_id not in iv.recused_from
            and not self._is_booked(iv.id, start)
        ]

 # return all potential start times where at least 2 interviewers are eligible
    def available_slots(self, candidate_id):
        all_starts = set().union(*(self.slots_for(iv) for iv in self.interviewers.values()))
        return sorted(
            s for s in all_starts
            if len(self.eligible_interviewers(candidate_id, s)) >= PANEL_SIZE
        )

# check if a valid two-interviewer panel can be assigned for a given candidate and start time
    def can_book(self, candidate_id, start):
        """Return whether a valid two-interviewer panel can be assigned."""
        return len(self.eligible_interviewers(candidate_id, start)) >= PANEL_SIZE

# subscribe to booking and cancellation updates, return a function to remove the subscription, and publish events to subscribers
    def subscribe(self, callback: Callable[[str, Interview], None]):
        self._subscribers.append(callback)

        def unsubscribe():
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    def _publish(self, event, interview):
        for callback in tuple(self._subscribers):
            callback(event, interview)

 
    def _load(self, interviewer_id):
        return sum(interviewer_id in i.interviewer_ids for i in self.interviews)

 #finds eligible interviewers, raise error if not enough, sort interviewers by current workload, select two least loaded interviewers, saves and returns new interview
    def book(self, candidate_id, start):
        with self._lock:
            pool = self.eligible_interviewers(candidate_id, start)
            if len(pool) < PANEL_SIZE:
                raise ValueError(
                    f"Need {PANEL_SIZE} interviewers, only {len(pool)} eligible"
                )
            pool.sort(key=lambda iv: (self._load(iv.id), iv.id))
            panel = [iv.id for iv in pool[:PANEL_SIZE]]
            interview = Interview(candidate_id, start, panel)
            self.interviews.append(interview)
        self._publish("booked", interview)
        return interview

# publish cancellation event to subscribers and return cancelled interviewer, but with an error if there is no matching interview
    def cancel_booking(self, candidate_id, start):
        with self._lock:
            for index, interview in enumerate(self.interviews):
                if interview.candidate_id == candidate_id and interview.start == start:
                    cancelled = self.interviews.pop(index)
                    break
            else:
                raise ValueError("Interview booking was not found")
        self._publish("cancelled", cancelled)
        return cancelled

# backward-compatible shorthand for cancel_booking()
    def cancel(self, candidate_id, start):
        """Backward-compatible shorthand for cancel_booking()."""
        return self.cancel_booking(candidate_id, start)
