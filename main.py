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
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])
CONFIG_FILE = "config.yml"
LOG_FILE = '/var/log/hitachi_content_platform.log'


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


class HCPCollector(object):

    def __init__(self, config):
       self.config = config
       self._metrics_values = {}
    
    def _setup_empty_prometheus_metrics(self):
        self._prometheus_metrics = {}
        for metric_config in self.config['metrics']:
            logging.debug("Add the metric '{}' to exporter".format(metric_config['metric_name']))
            label_name = [element['label_name'] for element in metric_config['labels']]
            self._prometheus_metrics[metric_config['metric_name']] = GaugeMetricFamily(metric_config['metric_name'], "Hitachi Content Platform {}".format(metric_config['metric_name']), labels=label_name)
    
    def _collect_info_from_urls(self):
        logging.info("Collect data from api list")
        headers = {
            'Authorization': self.config['Authorization'],
            'Accept': 'application/xml'
        }
        for key, value in self.config['endpoints'].items():
            if "<tentant-user>" not in value:
                logging.debug("Collect the api '{}'".format(self.config['base_url'] + value))
                res = requests.get(url=self.config['base_url'] + value, headers=headers, verify=False)
                root = etree.fromstring(res.content)
                tree = etree.ElementTree(root)
                self._metrics_values[key] = tree
            else:
                self._metrics_values[key] = dict()
                header_json = {
                    'Authorization': self.config['Authorization'],
                    'Accept': 'application/json'
                }
                res = requests.get(url=self.config['base_url'] + "/mapi/tenants", headers=header_json, verify=False)
                logging.debug("Tenants list: {}".format(res.text))
                tenants_list = json.loads(res.text)['name']
                for tenant in tenants_list:
                    url_tenant = self.config['base_url'] + value.replace("<tentant-user>", tenant)
                    logging.debug("Collect the api '{}'".format(url_tenant))
                    res = requests.get(url=url_tenant, headers=headers, verify=False)
                    root = etree.fromstring(res.content)
                    tree = etree.ElementTree(root)
                    self._metrics_values[key][tenant] = tree
    
    def populate_metrics(self):
        logging.info("Populate the metric exporter from http response")
        for metric_config in self.config['metrics']:
            if isinstance(self._metrics_values[metric_config['api_endpoint']], dict):
                # api contains tenant
                pass
            else:
                # api does not contain tenant
                tree = self._metrics_values[metric_config['api_endpoint']]
                for i in range(len(tree.xpath(metric_config['metric_path']))):
                    label_dict = {}
                    node = tree.xpath(metric_config['metric_path'])[i]
                    for element in metric_config['labels']:
                        label_node = node.xpath(element['label_path'])
                        label_dict[element['label_name']] = label_node[0].text
                    logging.debug("{}: {}".format(label_dict, node.text))
                    self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()), float(node.text))
    
    def collect(self):
        self._setup_empty_prometheus_metrics()
        self._collect_info_from_urls()
        self.populate_metrics()
        for metric in self._prometheus_metrics.values():
            yield metric

def main():
    pass


if __name__ == "__main__":
    config = load_config()
    start_http_server(8000)
    REGISTRY.register(HCPCollector(config))
    while True:
        time.sleep(10)