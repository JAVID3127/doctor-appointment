from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import heapq

@dataclass
class AppointmentRequest:
    request_id: str
    patient_id: int
    patient_name: str
    specialization: str
    start_time: datetime
    end_time: datetime
    priority: int = 1  # 1 = Normal, 2 = Urgent

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def overlaps_with(self, other: 'AppointmentRequest') -> bool:
        """Returns True if two appointment requests overlap in time."""
        return max(self.start_time, other.start_time) < min(self.end_time, other.end_time)

def earliest_finish_time_schedule(requests: List[AppointmentRequest]) -> List[AppointmentRequest]:
    """
    Classic Greedy Interval Scheduling (Earliest Finish Time - EFT).
    Selects the maximum-cardinality subset of mutually compatible requests for a single doctor.

    Mathematical Invariant:
    At each step, selecting the request that finishes earliest leaves the maximum
    possible remaining time for subsequent appointments.
    
    Time Complexity: O(n log n) for sorting + O(n) greedy selection.
    Space Complexity: O(n) to store accepted requests.
    """
    if not requests:
        return []

    # Sort requests by finish time (end_time ascending), then by priority descending
    sorted_requests = sorted(requests, key=lambda r: (r.end_time, -r.priority))

    accepted: List[AppointmentRequest] = []
    last_finish_time = datetime.min

    for req in sorted_requests:
        # If request starts at or after the finish time of the last accepted appointment
        if req.start_time >= last_finish_time:
            accepted.append(req)
            last_finish_time = req.end_time

    return accepted

def interval_partitioning_multidoctor(
    requests: List[AppointmentRequest],
    doctor_ids: List[int]
) -> Dict[int, List[AppointmentRequest]]:
    """
    Interval Partitioning Algorithm for Multi-Doctor Clinics.
    Assigns all compatible requests across parallel doctors using a Min-Heap.
    
    Invariant:
    Maintains a Min-Heap of doctors keyed by their current earliest available finish time.
    For each request (sorted by start time), we check if the earliest-free doctor is ready.
    If yes, allocate request to that doctor. If no and doctors remain, allocate to new doctor.
    
    Time Complexity: O(n log n) sorting + O(n log d) heap operations, where d = len(doctor_ids).
    """
    if not requests or not doctor_ids:
        return {doc_id: [] for doc_id in doctor_ids}

    # Sort requests strictly by start time
    sorted_requests = sorted(requests, key=lambda r: (r.start_time, r.end_time))

    # Min-heap storing tuples: (doctor_available_time, doctor_id)
    # Initially all doctors are available from datetime.min
    doc_heap: List[Tuple[datetime, int]] = []
    assigned_schedule: Dict[int, List[AppointmentRequest]] = {doc_id: [] for doc_id in doctor_ids}

    # Initialize heap with available doctors
    for doc_id in doctor_ids:
        heapq.heappush(doc_heap, (datetime.min, doc_id))

    unassigned: List[AppointmentRequest] = []

    for req in sorted_requests:
        earliest_finish, best_doc_id = heapq.heappop(doc_heap)

        if req.start_time >= earliest_finish:
            # Doctor is free to accept this request
            assigned_schedule[best_doc_id].append(req)
            heapq.heappush(doc_heap, (req.end_time, best_doc_id))
        else:
            # Doctor is busy; push back into heap
            heapq.heappush(doc_heap, (earliest_finish, best_doc_id))
            unassigned.append(req)

    return assigned_schedule

def compact_shift_schedule(
    shift_start: datetime,
    shift_end: datetime,
    requests: List[AppointmentRequest],
    buffer_mins: int = 0
) -> List[Tuple[datetime, datetime, AppointmentRequest]]:
    """
    Compact Greedy Packing:
    Packs consultation requests continuously starting from shift_start,
    eliminating idle gap times between appointments.
    """
    sorted_requests = sorted(requests, key=lambda r: (-r.priority, r.duration_minutes))
    packed = []
    curr = shift_start
    buffer_delta = timedelta(minutes=buffer_mins)

    for req in sorted_requests:
        dur = timedelta(minutes=req.duration_minutes)
        if curr + dur <= shift_end:
            slot_start = curr
            slot_end = curr + dur
            packed.append((slot_start, slot_end, req))
            curr = slot_end + buffer_delta
        else:
            break

    return packed
