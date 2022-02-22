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
import dicttoxml
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
        self.alert_labels = []
        self.custom_label = []
    
    def _setup_empty_prometheus_metrics(self):
        label_nodes = self.config['snodes'].copy()
        config_first_node = label_nodes[0]
        for node in label_nodes:
            if len(config_first_node) != len(node):
                logging.error("The number attributes in the config file for each node is not equal!")
                exit(1)
        custom_label = []
        for key in config_first_node:
            if key not in ['base_url', 'Authorization', 'node_name']:
                custom_label.append(key)
        self._prometheus_metrics = {}
        for metric_config in self.config['metrics']:
            logging.debug("Add the metric '{}' to exporter".format(metric_config['metric_name']))
            label_name = [element['label_name'] for element in metric_config['labels']]
            label_name.append('node')
            label_name += custom_label
            self._prometheus_metrics[metric_config['metric_name']] = GaugeMetricFamily(metric_config['metric_name'], "HCP S-node {}".format(metric_config['metric_name']), labels=label_name)
        # Add the alerts metric to exporters
        alert_labels = ['alertId', 'shortName', 'message', 'priority', 'severity', 'ticket', 'scope', 'scopeRef', 'level']
        alert_labels.remove(self.config['alert_config']['value'])
        self.alert_labels = ['node'] + custom_label + alert_labels
        self.custom_label = custom_label
        self._prometheus_metrics['alert'] = GaugeMetricFamily('alert', "HCP S-node alerts", labels=self.alert_labels)
    
    def _collect_info_from_urls(self):
        logging.info("Collect data from api list")
        # Other metrics
        for key, value in self.config['endpoints'].items():
            self._metrics_values[key] = dict()
            for node in self.config['snodes']:
                headers = {
                    'Authorization': node['Authorization'],
                    'X-HCPS-API-VERSION': '3.1.0'
                }
                result = requests.get(url=node['base_url'] + value, headers=headers, verify=False)
                data = json.loads(result.text)
                root = etree.fromstring(dicttoxml.dicttoxml(data))
                tree = etree.ElementTree(root)
                self._metrics_values[key][node['node_name']] = tree
        # Collect alerts
        self._metrics_values['alert'] = dict()
        for node in self.config['snodes']:
            headers = {
                    'Authorization': node['Authorization'],
                    'X-HCPS-API-VERSION': '3.1.0'
                }
            result = requests.get(url=node['base_url'] + '/mapi/alerts', headers=headers, verify=False)
            data = json.loads(result.text)
            for custom_lb in self.custom_label:
                data[custom_lb] = node[custom_lb]
            self._metrics_values['alert'][node['node_name']] = data

    def populate_metrics(self):
        logging.info("Populate the metric exporter from http response")
        # Other metrics
        for metric_config in self.config['metrics']:
            for node, data in self._metrics_values[metric_config['api_endpoint']].items():
                try:
                    leaf = data.xpath(metric_config['metric_path'])
                    for i in range(len(leaf)):
                        label_dict = {}
                        node_xm = leaf[i]
                        for element in metric_config['labels']:
                            label_node = node_xm.xpath(element['label_path'])
                            label_dict[element['label_name']] = label_node[0].text
                        logging.debug("metric '{}' label '{}' - {}: {}".format(metric_config['metric_name'], label_dict, node, node_xm.text))
                        number = extract_number(node_xm.text)
                        if number is not None:
                            label_values = [node]
                            for node_obj in self.config['snodes']:
                                if node_obj['node_name'] == node:
                                    for label in self.custom_label:
                                        label_values.append(str(node_obj[label]))
                            self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + label_values, number)
                        else:
                            pass
                except Exception as err:
                    logging.exception(err)
        # Alert metrics
        self.alert_labels.remove('node')
        for node, alert in self._metrics_values['alert'].items():
            if len(alert['alerts']) > 0:
                # There are alerts
                for alt in alert['alerts']:
                    for attribute in self.config['alert_config']['mapping_values']:
                        alt[attribute] = self.config['alert_config']['mapping_values'][attribute][alt[attribute]]
                    number = extract_number(alt[self.config['alert_config']['value']])
                    if number is not None:
                        label_values = [node]
                        for label in self.alert_labels:
                            if label in self.custom_label:
                                label_values.append(str(alert[label]))
                            else:
                                label_values.append(str(alt[label]))
                        self._prometheus_metrics['alert'].add_metric(label_values, number)
            else:
                # There is no alerts
                pass
    
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