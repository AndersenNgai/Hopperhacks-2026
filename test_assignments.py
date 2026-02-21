import assignments
import time

# Add some test tasks
assignments.add_assignment("Finish calculus homework", 60, "2026-02-25", "high")
assignments.add_assignment("Study for midterm", 120, "2026-03-01", "medium")
assignments.add_assignment("Read chapter 5", 30, "", "low")

print(assignments.get_summary())

# Start Pomodoro
assignments.start_pomodoro()

# Let it run for 30 seconds (just to test)
time.sleep(30)

assignments.stop_pomodoro()