"""Generic action library, used for suggested actions when no RCA is known as of the replay
date (SPEC 5.7, replay rule in docs/SPEC.md Part 1). Written from general maintenance practice,
per diagnosis rule: two corrective and two preventive actions. The RCA text is not copied here.

Each suggestion built from this list carries source "action_library" in the API response, so the
UI can label it as a generic suggestion rather than an RCA-derived one.
"""

ACTION_LIBRARY: dict[str, list[dict]] = {
    "Seal leakage (pump)": [
        {"category": "corrective", "text": "Replace the pump mechanical seal and inspect the seal faces for damage."},
        {"category": "corrective", "text": "Check the seal flush flow path and clean or replace the flush line filter."},
        {"category": "preventive", "text": "Add seal flush flow and seal chamber pressure to the daily round with an alarm threshold."},
        {"category": "preventive", "text": "Review seal selection against the current process conditions and operating window."},
    ],
    "Lube oil water ingress, bearing distress (compressor)": [
        {"category": "corrective", "text": "Find and isolate the lube oil cooler leak, then pressure-test the cooler before return to service."},
        {"category": "corrective", "text": "Drain and replace the lube oil, then confirm water content is back within its limit."},
        {"category": "preventive", "text": "Trend lube oil water content weekly and set a pre-alarm level below the alarm limit."},
        {"category": "preventive", "text": "Inspect lube oil cooler gaskets and tube-to-tubesheet joints at each planned shutdown."},
    ],
    "Motor bearing lubrication failure": [
        {"category": "corrective", "text": "Re-grease the motor drive-end bearing to the correct quantity and interval, then check bearing temperature."},
        {"category": "corrective", "text": "Inspect the drive-end bearing for wear and replace it if vibration stays high after re-greasing."},
        {"category": "preventive", "text": "Set an automatic lubrication schedule and check grease condition at each route visit."},
        {"category": "preventive", "text": "Add motor drive-end bearing temperature and motor vibration to the condition-monitoring route."},
    ],
    "Exchanger fouling": [
        {"category": "corrective", "text": "Clean the tube bundle and verify the tube-side differential pressure returns to its baseline."},
        {"category": "corrective", "text": "Check the feed for heavy ends and adjust upstream operation to slow the fouling."},
        {"category": "preventive", "text": "Trend tube-side differential pressure and heat duty weekly to plan cleaning before the alarm limit."},
        {"category": "preventive", "text": "Set the cleaning interval from the measured fouling rate instead of a fixed calendar."},
    ],
    "Coupling misalignment": [
        {"category": "corrective", "text": "Perform a laser alignment check and correct the coupling offset to the manufacturer tolerance."},
        {"category": "corrective", "text": "Inspect the coupling elements and replace worn parts before re-aligning."},
        {"category": "preventive", "text": "Check alignment after every maintenance job on the driver or the driven machine."},
        {"category": "preventive", "text": "Add a 2X harmonic check to the vibration route to catch misalignment early."},
    ],
}
