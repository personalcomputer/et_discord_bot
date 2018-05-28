import datetime


def get_time_until_next_interval_start(current_datetime, interval_period):
    # Interval period must fit within 24 hours and interval period must evenly divide within 24 hours, such that a
    # period can always start at midnight.
    assert(interval_period <= datetime.timedelta(hours=24))
    assert((datetime.timedelta(hours=24) % interval_period).total_seconds() == 0)

    current_time = current_datetime.time()
    current_time_as_dt = datetime.timedelta(
        seconds=current_time.hour*60*60 + current_time.minute*60 + current_time.second,
        microseconds=current_time.microsecond
    )
    return interval_period - (current_time_as_dt % interval_period)


def split_chunks(sequence, chunk_length):
    return (sequence[i:i+chunk_length] for i in range(0, len(sequence), chunk_length))
