import enum
from typing import Dict, Set

class AppointmentState(str, enum.Enum):
    BOOKED = "BOOKED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    IN_CONSULTATION = "IN_CONSULTATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class InvalidStateTransitionError(Exception):
    """Raised when an illegal transition is attempted on an appointment."""
    pass

class AppointmentStateMachine:
    """
    Encapsulates state machine logic for hospital appointment status transitions.
    Enforces strict business rules (e.g., patient must check in before entering consultation).
    """

    ALLOWED_TRANSITIONS: Dict[AppointmentState, Set[AppointmentState]] = {
        AppointmentState.BOOKED: {
            AppointmentState.CONFIRMED,
            AppointmentState.CANCELLED
        },
        AppointmentState.CONFIRMED: {
            AppointmentState.CHECKED_IN,
            AppointmentState.CANCELLED,
            AppointmentState.NO_SHOW
        },
        AppointmentState.CHECKED_IN: {
            AppointmentState.IN_CONSULTATION,
            AppointmentState.CANCELLED,
            AppointmentState.NO_SHOW
        },
        AppointmentState.IN_CONSULTATION: {
            AppointmentState.COMPLETED
        },
        # Terminal states
        AppointmentState.COMPLETED: set(),
        AppointmentState.CANCELLED: set(),
        AppointmentState.NO_SHOW: set()
    }

    @classmethod
    def can_transition(cls, current_state: AppointmentState, next_state: AppointmentState) -> bool:
        """Returns True if transition from current_state to next_state is valid."""
        return next_state in cls.ALLOWED_TRANSITIONS.get(current_state, set())

    @classmethod
    def validate_transition(cls, current_state: AppointmentState, next_state: AppointmentState):
        """Raises InvalidStateTransitionError if transition is illegal."""
        if not cls.can_transition(current_state, next_state):
            raise InvalidStateTransitionError(
                f"Cannot transition appointment from '{current_state.value}' to '{next_state.value}'. "
                f"Allowed target states: {[s.value for s in cls.ALLOWED_TRANSITIONS.get(current_state, set())]}"
            )
