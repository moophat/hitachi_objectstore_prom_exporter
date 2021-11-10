from prometheus_client.core import GaugeMetricFamily, REGISTRY
from prometheus_client import start_http_server
import random
import time


class IBMCollector(object):
    def __init__(self):
        pass

    def collect(self):
        g = GaugeMetricFamily("RandomNumber", 'Just test', labels=['instance'])
        g.add_metric(["testing number"], random.random())
        yield g


if __name__ == '__main__':
    start_http_server(8000)
    REGISTRY.register(IBMCollector())
    while True:
        time.sleep(10)