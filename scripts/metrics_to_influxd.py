#!/usr/bin/env python3
#
# metrics_to_influxd.py
# requires celery with redis (e.g. python3-celery python3-redis)

import argparse
import signal
from datetime import datetime

from celery import Celery

TS = int(datetime.utcnow().replace(microsecond=0).timestamp() * 1000_000_000)


def my_monitor(app):
    state = app.events.State()

    def announce_failed_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        try:
            short_name = task.name.split(".")[-1]
        except (AttributeError, IndexError):
            short_name = "unknown"

        runtime = task.info().get("runtime")
        if runtime:
            print(f'tasks,status=failed,name={short_name},fullname={task.name} {runtime} {TS}')
        else:
            print(f'tasks,status=failed,name={short_name},fullname={task.name} 0.0 {TS}')

    def announce_succeeded_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        try:
            short_name = task.name.split(".")[-1]
        except (AttributeError, IndexError):
            short_name = "unknown"
        runtime = task.info().get("runtime")

        if runtime:
            print(f'tasks,status=succeeded,name={short_name},fullname={task.name} {runtime} {TS}')
        else:
            print(f'tasks,status=succeeded,name={short_name},fullname={task.name} 0.0 {TS}')

    with app.connection() as connection:
        recv = app.events.Receiver(connection, handlers={
            'task-failed': announce_failed_tasks,
            'task-succeeded': announce_succeeded_tasks,
            '*': state.event,
        })
        recv.capture(limit=None, timeout=None, wakeup=True)


def main():
    # make sure CTRL+C works
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # create the top-level parser
    parser = argparse.ArgumentParser(description="Monitor (blocking) Redis "
                                                 "for Task stats and format "
                                                 "in InfluxDB line format")

    parser.add_argument("-V", "--version",
                        help="print version", action="version",
                        version="0.1")

    parser.add_argument("-H", "--host", dest="host", default="127.0.0.1",
                        help="Host for Redis", type=str)

    parser.add_argument("-P", "--port", dest="port", default=6379,
                        help="Port for Redis", type=int)

    parser.add_argument("-p", "--password", dest="password", default=None,
                        help="Password for Redis", type=str)

    # parse args
    args = parser.parse_args()

    app = Celery(broker=f'redis://{args.host}:{args.port}/0')
    my_monitor(app)


if __name__ == "__main__":
    main()
