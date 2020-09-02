#!/usr/bin/env python3
#
# metrics_to_influxd.py
# requires celery with redis (e.g. python3-celery python3-redis)

import argparse
import os
import signal
from datetime import datetime

from celery import Celery
from influxdb import InfluxDBClient


def influx_write_point(client, measurement, tags, fields, time=None):
    if not time:
        ts = int(datetime.utcnow().replace(microsecond=0).timestamp() * 1000_000_000)
        time = ts

    json_body = [
        {
            "measurement": measurement,
            "tags": tags,
            "time": time,
            "fields": fields
        }
    ]

    try:
        result = client.write_points(json_body)
        print(f"write result: {result}")
    except Exception as err:
        print(f"an error occurred: {err}")


def my_monitor(app, client, hostname):
    state = app.events.State()

    def announce_failed_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        ts = int(datetime.utcnow().replace(microsecond=0).timestamp() * 1000_000_000)
        try:
            short_name = task.name.split(".")[-1]
        except (AttributeError, IndexError):
            short_name = "unknown"

        runtime = task.info().get("runtime")
        if runtime:
            print(f'tasks,status=failed,name={short_name},fullname={task.name} runtime={runtime} {ts}')
            influx_write_point(client, 'tasks',
                               tags={'host': hostname, 'status': 'failed',
                                     'name': short_name, 'fullname': task.name},
                               fields={'runtime': runtime})
        else:
            print(f'tasks,status=failed,name={short_name},fullname={task.name} runtime=0.0 {ts}')
            influx_write_point(client, 'tasks',
                               tags={'host': hostname, 'status': 'failed',
                                     'name': short_name, 'fullname': task.name},
                               fields={'runtime': runtime})

    def announce_succeeded_tasks(event):
        state.event(event)
        # task name is sent only with -received event, and state
        # will keep track of this for us.
        task = state.tasks.get(event['uuid'])

        ts = int(datetime.utcnow().replace(microsecond=0).timestamp() * 1000_000_000)
        try:
            short_name = task.name.split(".")[-1]
        except (AttributeError, IndexError):
            short_name = "unknown"

        runtime = task.info().get("runtime")
        if runtime:
            print(f'tasks,status=succeeded,name={short_name},fullname={task.name} runtime={runtime} {ts}')
            influx_write_point(client, 'tasks',
                               tags={'host': hostname, 'status': 'succeeded',
                                     'name': short_name, 'fullname': task.name},
                               fields={'runtime': runtime})
        else:
            print(f'tasks,status=succeeded,name={short_name},fullname={task.name} runtime=0.0 {ts}')
            influx_write_point(client, 'tasks',
                               tags={'host': hostname, 'status': 'succeeded',
                                     'name': short_name, 'fullname': task.name},
                               fields={'runtime': runtime})

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

    parser.add_argument("--hostname", dest="hostname",
                        default=os.environ.get("METRICS_INFLUX_TAG_HOSTNAME", "localhost"),
                        help="System Hostname (Tag)", type=str)

    parser.add_argument("-H", "--host", dest="host",
                        default=os.environ.get("METRICS_INFLUX_HOST", "127.0.0.1"),
                        help="Host for InfluxDB", type=str)

    parser.add_argument("-P", "--port", dest="port",
                        default=os.environ.get("METRICS_INFLUX_PORT", "8086"),
                        help="Port for InfluxDB", type=str)

    parser.add_argument("-u", "--username", dest="username",
                        default=os.environ.get("METRICS_INFLUX_USER", "ip2tor"),
                        help="Username for InfluxDB", type=str)

    parser.add_argument("-p", "--password", dest="password",
                        default=os.environ.get("METRICS_INFLUX_PASS", "ip2tor"),
                        help="Password for InfluxDB", type=str)

    parser.add_argument("-d", "--database", dest="database",
                        default=os.environ.get("METRICS_INFLUX_DATABASE", "ip2tor"),
                        help="Database for InfluxDB", type=str)

    parser.add_argument("-s", "--ssl", dest="ssl", default=True,
                        help="SSL for InfluxDB", type=bool)

    parser.add_argument("--verify", dest="verify", default=True,
                        help="Verify for InfluxDB", type=bool)

    parser.add_argument("--redis-host", dest="redis_host", default="127.0.0.1",
                        help="Host for Redis", type=str)

    parser.add_argument("--redis-port", dest="redis_port", default=6379,
                        help="Port for Redis", type=int)

    parser.add_argument("--redis-password", dest="redis_password", default=None,
                        help="Password for Redis", type=str)

    # parse args
    args = parser.parse_args()

    client = InfluxDBClient(args.host, args.port,
                            args.username, args.password, args.database, args.ssl, args.verify,
                            timeout=30)

    app = Celery(broker=f'redis://{args.redis_host}:{args.redis_port}/0')
    my_monitor(app, client, args.hostname)


if __name__ == "__main__":
    main()
