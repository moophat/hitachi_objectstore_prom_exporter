from prometheus_client.core import GaugeMetricFamily, REGISTRY
import yaml
from yaml.scanner import ScannerError
import logging
import os
import requests
from lxml import etree
import json
import urllib3
from prometheus_client import start_http_server, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR
import time
import re
import jmespath
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])
CONFIG_FILE = "config.yml"
LOG_FILE = '/var/log/hitachi_S_series.log'
config = {}


def extract_number(text):
    result = None
    try:
        result = float(text)
    except:
        rst = re.findall(r"[-+]?\d*\.\d+|\d+", text)
        if len(rst) > 0:
            result = float(rst[0])
        else:
            pass
    return result


def load_config():
    # load yaml config
    config_file_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
    if os.path.isfile(config_file_path):
        with open(config_file_path, "r") as f:
            try:
                yaml_config = yaml.safe_load(f)
                f.close()
            except ScannerError:
                print("Can not load the file config.yml!")
            finally:
                f.close()
            return yaml_config
    else:
        print("Can not find the file config.yml!")
        exit(0)

def config_logging(log_file):
    if config['debug']:
        logging.basicConfig(
            filename=log_file,
            filemode='a',
            format='%(asctime)s   %(levelname)s   %(message)s',
            level=logging.DEBUG)
    else:
        logging.basicConfig(
            filename=log_file,
            filemode='a',
            format='%(asctime)s   %(levelname)s   %(message)s',
            level=logging.INFO)

class HCPSnode(object):

    def __init__(self, config):
        self.config = config
        self._metrics_values = {}
    
    def _setup_empty_prometheus_metrics(self):
        self._prometheus_metrics = {}
        for metric_config in self.config['metrics']:
            logging.debug("Add the metric '{}' to exporter".format(metric_config['metric_name']))
            label_name = ['node']
            self._prometheus_metrics[metric_config['metric_name']] = GaugeMetricFamily(metric_config['metric_name'], "HCP S-node {}".format(metric_config['metric_name']), labels=label_name)
    
    def _collect_info_from_urls(self):
        logging.info("Collect data from api list")
        for key, value in self.config['endpoints'].items():
            self._metrics_values[key] = dict()
            for node in self.config['snodes']:
                headers = {
                    'Authorization': node['Authorization'],
                    'X-HCPS-API-VERSION': '3.1.0'
                }
                result = requests.get(url=node['base_url'] + value, headers=headers, verify=False)
                data = json.loads(result.text)
                self._metrics_values[key][node['node_name']] = data

    def populate_metrics(self):
        logging.info("Populate the metric exporter from http response")
        for metric_config in self.config['metrics']:
            for node, data in self._metrics_values[metric_config['api_endpoint']].items():
                try:
                    number = jmespath.search(metric_config['metric_path'], data=data)
                    self._prometheus_metrics[metric_config['metric_name']].add_metric([node], number)
                except Exception as err:
                    logging.exception(err)
    
    def collect(self):
        self._setup_empty_prometheus_metrics()
        self._collect_info_from_urls()
        self.populate_metrics()
        for metric in self._prometheus_metrics.values():
            yield metric
    

def main():
    global config
    config = load_config()
    if config.get('log_file'):
        log_file = config['log_file']
    else:
        log_file = LOG_FILE
    config_logging(log_file)
    start_http_server(int(config.get('port')), config.get('host'))
    REGISTRY.register(HCPSnode(config))
    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()