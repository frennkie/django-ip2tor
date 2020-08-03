#!/usr/bin/env python3
#
# metrics_to_influx.py
# requires e.g. python3-redis
import argparse
import signal
from datetime import datetime

import redis

TS = int(datetime.utcnow().replace(microsecond=0).timestamp() * 1000_000_000)


def redis_connection(host: str, port: int, password: str):
    con = redis.Redis(host=host, port=port, password=password)
    return con


def get_from_redis(con, key: str) -> dict:
    results = con.hgetall(key)

    return results


def get_payment_from_redis(con, key: str):
    results = con.lpop(key)

    return results


def to_influx_line(data: dict, bridge_host: str = "bridge_host") -> str:
    initial = int(data.get(b"I", 0))
    needs_activate = int(data.get(b"P", 0))
    active = int(data.get(b"A", 0))
    needs_suspend = int(data.get(b"S", 0))
    suspended = int(data.get(b"H", 0))
    archived = int(data.get(b"Z", 0))
    needs_delete = int(data.get(b"D", 0))
    failed = int(data.get(b"F", 0))

    return (
        f'bridge_fields'
        f',bridge_host={bridge_host}'
        f' I={initial}i'
        f',P={needs_activate}i'
        f',A={active}i'
        f',S={needs_suspend}i'
        f',H={suspended}i'
        f',Z={archived}i'
        f',D={needs_delete}i'
        f',F={failed}i'
        f' {TS}'
    )


def to_influx_lines_as_tags(data: dict, bridge_host: str = "bridge_host") -> list:
    initial = int(data.get(b"I", 0))
    needs_activate = int(data.get(b"P", 0))
    active = int(data.get(b"A", 0))
    needs_suspend = int(data.get(b"S", 0))
    suspended = int(data.get(b"H", 0))
    archived = int(data.get(b"Z", 0))
    needs_delete = int(data.get(b"D", 0))
    failed = int(data.get(b"F", 0))

    return [
        f'bridge,bridge_host={bridge_host},status=initial count={initial}i {TS}',
        f'bridge,bridge_host={bridge_host},status=needs_activate count={needs_activate}i {TS}',
        f'bridge,bridge_host={bridge_host},status=active count={active}i {TS}',
        f'bridge,bridge_host={bridge_host},status=needs_suspend count={needs_suspend}i {TS}',
        f'bridge,bridge_host={bridge_host},status=suspended count={suspended}i {TS}',
        f'bridge,bridge_host={bridge_host},status=archived count={archived}i {TS}',
        f'bridge,bridge_host={bridge_host},status=needs_delete count={needs_delete}i {TS}',
        f'bridge,bridge_host={bridge_host},status=failed count={failed}i {TS}',
    ]


def main():
    # make sure CTRL+C works
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # create the top-level parser
    parser = argparse.ArgumentParser(description="get Metrics from Redis "
                                                 "and format in InfluxDB "
                                                 "line format")

    parser.add_argument("-V", "--version",
                        help="print version", action="version",
                        version="0.1")

    parser.add_argument("-H", "--host", dest="host", default="127.0.0.1",
                        help="Host for Redis", type=str)

    parser.add_argument("-P", "--port", dest="port", default=6379,
                        help="Port for Redis", type=int)

    parser.add_argument("-p", "--password", dest="password", default=None,
                        help="Password for Redis", type=str)

    parser.add_argument("-f", "--fields", help="Use fields/columns instead of tags", action='store_true')

    # parse args
    args = parser.parse_args()

    con = redis_connection(args.host, args.port, args.password)

    keys = con.keys('ip2tor.metrics.torbridge.status.*')
    for full_key in keys:
        key = full_key.decode()
        bridge_host = key.split(".")[-1:][0]
        torbridge_status = get_from_redis(con, key=key)

        if args.fields:
            data = to_influx_line(torbridge_status, bridge_host=bridge_host)
            print(data)
        else:
            data = to_influx_lines_as_tags(torbridge_status, bridge_host=bridge_host)
            print("\n".join(data))

    payment = get_payment_from_redis(con, "ip2tor.metrics.payments.sats")
    try:
        print(f'payments sats={int(payment)}i {TS}')
    except (TypeError, ValueError):
        pass


if __name__ == "__main__":
    main()
