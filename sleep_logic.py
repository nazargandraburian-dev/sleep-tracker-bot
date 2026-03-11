from datetime import datetime

def calculate_sleep(bed, wake):
    bed_time = datetime.fromisoformat(bed)
    wake_time = datetime.fromisoformat(wake)

    duration = wake_time - bed_time
    minutes = int(duration.total_seconds() / 60)

    hours = minutes / 60

    if hours < 5:
        score = 2
        comment = "Very little sleep 😵"
    elif hours < 6:
        score = 4
        comment = "Too little sleep 😕"
    elif hours < 7:
        score = 6
        comment = "Could be better 😐"
    elif hours < 8:
        score = 7
        comment = "Slightly below ideal 🙂"
    elif hours < 9:
        score = 10
        comment = "Perfect sleep! 😄"
    elif hours < 10:
        score = 9
        comment = "Great sleep 😌"
    elif hours < 10.5:
        score = 8
        comment = "A bit long 😴"
    else:
        score = 6
        comment = "Too much sleep 😵‍💫"

    return minutes, score, comment
