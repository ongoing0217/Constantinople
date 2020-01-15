import time

def timer(func):
    def wrapper_timer(*args, **kwargs):
        start_time=time.time()
        value=func(*args, **kwargs)
        end_time=time.time()
        run_time=end_time-start_time
        print(str(run_time) + 's taken')
        return value
    return wrapper_timer
