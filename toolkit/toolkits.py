import pandas as pd
from typing import Literal
from langchain_core.tools import tool
from data_models.models import DateModel, DateTimeModel, IdentificationNumberModel
from utils.notifications import notify_booking, notify_cancellation

CSV_PATH = "doctor_availability.csv"

DOCTOR_NAMES = Literal[
    'kevin anderson', 'robert martinez', 'susan davis', 'daniel miller',
    'sarah wilson', 'michael green', 'lisa brown', 'jane smith',
    'emily johnson', 'john doe'
]

SPECIALIZATIONS = Literal[
    "general_dentist", "cosmetic_dentist", "prosthodontist",
    "pediatric_dentist", "emergency_dentist", "oral_surgeon", "orthodontist"
]


# ─── Helper ───────────────────────────────────────────────────────────────────

def _convert_datetime_format(dt_str: str) -> str:
    """Convert 'DD-MM-YYYY HH:MM' → 'DD-MM-YYYY H.M' (CSV format)."""
    from datetime import datetime
    dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M")
    return dt.strftime("%d-%m-%Y %#H.%M")   # Windows-safe; on Linux use %-H.%-M


def _convert_to_am_pm(time_str: str) -> str:
    time_str = str(time_str)
    hours, minutes = map(int, time_str.split(":"))
    period = "AM" if hours < 12 else "PM"
    hours = hours % 12 or 12
    return f"{hours}:{minutes:02d} {period}"


# ─── Tools ────────────────────────────────────────────────────────────────────

@tool
def check_availability_by_doctor(desired_date: DateModel, doctor_name: DOCTOR_NAMES):
    """
    Check database availability for a specific doctor on a given date.
    The parameters should be mentioned by the user in the query.
    """
    df = pd.read_csv(CSV_PATH)
    df['date_slot_time'] = df['date_slot'].apply(lambda x: x.split(' ')[-1])

    rows = list(
        df[
            (df['date_slot'].apply(lambda x: x.split(' ')[0]) == desired_date.date) &
            (df['doctor_name'] == doctor_name) &
            (df['is_available'] == True)
        ]['date_slot_time']
    )

    if not rows:
        return "No availability in the entire day."
    return (
        f"Availability for {desired_date.date}:\n"
        "Available slots: " + ', '.join(rows)
    )


@tool
def check_availability_by_specialization(desired_date: DateModel, specialization: SPECIALIZATIONS):
    """
    Check database availability for a specific specialization on a given date.
    The parameters should be mentioned by the user in the query.
    """
    df = pd.read_csv(CSV_PATH)
    df['date_slot_time'] = df['date_slot'].apply(lambda x: x.split(' ')[-1])

    rows = (
        df[
            (df['date_slot'].apply(lambda x: x.split(' ')[0]) == desired_date.date) &
            (df['specialization'] == specialization) &
            (df['is_available'] == True)
        ]
        .groupby(['specialization', 'doctor_name'])['date_slot_time']
        .apply(list)
        .reset_index(name='available_slots')
    )

    if rows.empty:
        return "No availability in the entire day."

    output = f"Availability for {desired_date.date}:\n"
    for row in rows.values:
        output += row[1] + ". Available slots:\n"
        output += ', '.join([_convert_to_am_pm(v) for v in row[2]]) + '\n'
    return output


@tool
def set_appointment(
    desired_date: DateTimeModel,
    id_number: IdentificationNumberModel,
    doctor_name: DOCTOR_NAMES
):
    """
    Book an appointment slot with the doctor.
    The parameters MUST be mentioned by the user in the query.
    Sends a confirmation email notification to the patient after booking.
    """
    df = pd.read_csv(CSV_PATH)

    try:
        csv_date = _convert_datetime_format(desired_date.date)
    except Exception:
        csv_date = desired_date.date  # fall through, will return not-found

    case = df[
        (df['date_slot'] == csv_date) &
        (df['doctor_name'] == doctor_name) &
        (df['is_available'] == True)
    ]

    if case.empty:
        return "No available appointments for that slot."

    df.loc[
        (df['date_slot'] == csv_date) &
        (df['doctor_name'] == doctor_name) &
        (df['is_available'] == True),
        ['is_available', 'patient_to_attend']
    ] = [False, id_number.id]

    df.to_csv(CSV_PATH, index=False)

    # Send notification email
    notif = notify_booking(id_number.id, doctor_name, desired_date.date)
    return f"Appointment successfully booked. {notif}"


@tool
def cancel_appointment(
    date: DateTimeModel,
    id_number: IdentificationNumberModel,
    doctor_name: DOCTOR_NAMES
):
    """
    Cancel an existing appointment.
    The parameters MUST be mentioned by the user in the query.
    Sends a cancellation email notification to the patient.
    """
    df = pd.read_csv(CSV_PATH)

    case_to_remove = df[
        (df['date_slot'] == date.date) &
        (df['patient_to_attend'] == id_number.id) &
        (df['doctor_name'] == doctor_name)
    ]

    if case_to_remove.empty:
        return "No appointment found with those specifications."

    df.loc[
        (df['date_slot'] == date.date) &
        (df['patient_to_attend'] == id_number.id) &
        (df['doctor_name'] == doctor_name),
        ['is_available', 'patient_to_attend']
    ] = [True, None]

    df.to_csv(CSV_PATH, index=False)

    # Send notification email
    notif = notify_cancellation(id_number.id, doctor_name, date.date)
    return f"Appointment successfully cancelled. {notif}"


@tool
def reschedule_appointment(
    old_date: DateTimeModel,
    new_date: DateTimeModel,
    id_number: IdentificationNumberModel,
    doctor_name: DOCTOR_NAMES
):
    """
    Reschedule an existing appointment to a new date/time.
    The parameters MUST be mentioned by the user in the query.
    Sends notification emails for both the cancellation and new booking.
    """
    df = pd.read_csv(CSV_PATH)

    available = df[
        (df['date_slot'] == new_date.date) &
        (df['is_available'] == True) &
        (df['doctor_name'] == doctor_name)
    ]

    if available.empty:
        return "No available slots in the desired period."

    # Cancel old, book new (each sends its own notification)
    cancel_result = cancel_appointment.invoke({
        'date': old_date, 'id_number': id_number, 'doctor_name': doctor_name
    })
    book_result = set_appointment.invoke({
        'desired_date': new_date, 'id_number': id_number, 'doctor_name': doctor_name
    })

    return f"Appointment successfully rescheduled.\n{cancel_result}\n{book_result}"