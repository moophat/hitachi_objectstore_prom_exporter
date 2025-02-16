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
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])
CONFIG_FILE = "config.yml"
LOG_FILE = '/var/log/hitachi_content_platform.log'
config = {}
defs = {'GB': 1, 'TB': 1024, 'PB': 1024 * 1024}


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


def convert_hard_quota(text):
    try:
        token = text.split()
        if len(token) < 2:
            logging.error("Can not convert the hard quota: %s, return -1 as a value error" % text)
            return -1
        else:
            value  = float(token[0].replace(",", "")) * defs[token[1]]
            return value
    except Exception as err:
        logging.error(err)
        logging.error("Can not convert the hard quota: %s, return -1 as a value error" % text)
        return -1


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


def check_state(text):
    state = {"READY": 0, "RUNNING": 1, "DISABLED": 2}
    if text in state:
        return state[text]
    else:
        return None


class HCPCollector(object):

    def __init__(self, config):
        self.config = config
        self._metrics_values = {}
        self.custom_labels = {}
        if 'custom_label' in config:
            for custom_label in config['custom_label']:
                self.custom_labels[custom_label['label_name']] = custom_label['label_value']
            
    
    def _setup_empty_prometheus_metrics(self):
        self._prometheus_metrics = {}
        for metric_config in self.config['metrics']:
            logging.debug("Add the metric '{}' to exporter".format(metric_config['metric_name']))
            label_name = [element['label_name'] for element in metric_config['labels']]
            if "<tenant-user>" in self.config['endpoints'][metric_config['api_endpoint']]:
                label_name.append('tenant')
            if "<namespace>" in self.config['endpoints'][metric_config['api_endpoint']]:
                label_name.append('namespace')
            label_name += list(self.custom_labels.keys())
            self._prometheus_metrics[metric_config['metric_name']] = GaugeMetricFamily(metric_config['metric_name'], "Hitachi Content Platform {}".format(metric_config['metric_name']), labels=label_name)
        self._prometheus_metrics['node_connection'] = GaugeMetricFamily('node_connection', "HCP G-node connection", labels=list(self.custom_labels.keys()))
    
    def _collect_info_from_urls(self):
        if 'timeout' in self.config:
            timeout = float(self.config['timeout'])
        else:
            timeout = 3
        logging.info("Collect data from api list")
        self._metrics_values['node_connection'] = 1
        headers = {
            'Authorization': self.config['Authorization'],
            'Accept': 'application/xml'
        }
        # Get all tenant user and namespaces - Start
        header_json = {
            'Authorization': self.config['Authorization'],
            'Accept': 'application/json'
        }
        tenants_dict = dict()
        try:
            res = requests.get(url=self.config['base_url'] + "/mapi/tenants", headers=header_json, verify=False, timeout=timeout)
            logging.debug("Tenants list: {}".format(res.text))
            # tenants_dict = json.loads(res.text)['name']
            for tenant in json.loads(res.text)['name']:
                # Get all namespaces belong to tenant - Start
                res1 = requests.get(url=self.config['base_url'] + "/mapi/tenants/" + tenant + "/namespaces", headers=header_json, verify=False, timeout=timeout)
                logging.debug("namespace list in tenant '{}': '{}'".format(tenant, res1.text))
                try:
                    tenants_dict[tenant] = json.loads(res1.text)['name']
                except:
                    tenants_dict[tenant] = []
                    logging.error("Error with tenant {}: output namespace is {}".format(tenant, res1.text))
                # Get all namespaces belong to tenant - End
        except Exception as err:
            logging.error("Error to get tenants list and namespace")
            logging.exception(err)
            self._metrics_values['node_connection'] = 0
        # Get all tenant user and namespaces - End
        for key, value in self.config['endpoints'].items():
            if "<tenant-user>" not in value:
                logging.debug("Collect the api '{}'".format(self.config['base_url'] + value))
                try:
                    res = requests.get(url=self.config['base_url'] + value, headers=headers, verify=False, timeout=timeout)
                    root = etree.fromstring(res.content)
                    tree = etree.ElementTree(root)
                    self._metrics_values[key] = tree
                except Exception as err:
                    logging.error("Error to get data from api '{}'".format(self.config['base_url'] + value))
                    logging.exception(err)
                    self._metrics_values['node_connection'] = 0
            else:
                self._metrics_values[key] = dict()
                if "<namespace>" not in value:
                    for tenant in tenants_dict:
                        url_tenant = self.config['base_url'] + value.replace("<tenant-user>", tenant)
                        logging.debug("Collect the api '{}'".format(url_tenant))
                        try:
                            res = requests.get(url=url_tenant, headers=headers, verify=False, timeout=timeout)
                            root = etree.fromstring(res.content)
                            tree = etree.ElementTree(root)
                            self._metrics_values[key][tenant] = tree
                        except Exception as err:
                            logging.error("Error to get data from api '{}'".format(url_tenant))
                            logging.exception(err)
                            self._metrics_values['node_connection'] = 0
                else:
                    for tenant in tenants_dict:
                        self._metrics_values[key][tenant] = dict()
                        for namespace in tenants_dict[tenant]:
                            url_namespace = self.config['base_url'] + value.replace("<tenant-user>", tenant).replace("<namespace>", namespace)
                            logging.debug("Collect the api '{}'".format(url_namespace))
                            try:
                                res = requests.get(url=url_namespace, headers=headers, verify=False, timeout=timeout)
                                root = etree.fromstring(res.content)
                                tree = etree.ElementTree(root)
                                self._metrics_values[key][tenant][namespace] = tree
                            except Exception as err:
                                logging.error("Error to get data from api '{}'".format(url_namespace))
                                logging.exception(err)
                                self._metrics_values['node_connection'] = 0
    
    def populate_metrics(self):
        logging.info("Populate the metric exporter from http response")
        # Add connection metric
        self._prometheus_metrics['node_connection'].add_metric([] + list(self.custom_labels.values()), self._metrics_values['node_connection'])
        # Add other metrics
        for metric_config in self.config['metrics']:
            if isinstance(self._metrics_values[metric_config['api_endpoint']], dict):
                # api contains tenant
                for tenant, value in self._metrics_values[metric_config['api_endpoint']].items():
                    if not isinstance(value, dict):
                        # api does not contain namespace
                        leaf = value.xpath(metric_config['metric_path'])
                        for i in range(len(leaf)):
                            label_dict = {}
                            node = leaf[i]
                            for element in metric_config['labels']:
                                label_node = node.xpath(element['label_path'])
                                label_dict[element['label_name']] = label_node[0].text
                            logging.debug("metric '{}' label '{}' - {}: {}".format(metric_config['metric_name'], label_dict, tenant, node.text))
                            number = extract_number(node.text)
                            if number is not None:
                                # Hard code check hard quota - Start
                                if 'hardQuota' in metric_config['metric_path']:
                                    number = convert_hard_quota(node.text)
                                # Hard code check hard quota - End
                                self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + [tenant] + list(self.custom_labels.values()), number)
                            else:
                                # Get non numeric data
                                check_st = check_state(node.text)
                                if check_st is not None:
                                    # Hard code for service state
                                    self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + [tenant] + list(self.custom_labels.values()), check_st)
                                else:
                                    # Does not support the non numeric data
                                    pass
                    else:
                        # api contains tenant and namespace
                        for namespace, nsdata in value.items():
                            leaf = nsdata.xpath(metric_config['metric_path'])
                            for i in range(len(leaf)):
                                label_dict = {}
                                node = leaf[i]
                                for element in metric_config['labels']:
                                    label_node = node.xpath(element['label_path'])
                                    label_dict[element['label_name']] = label_node[0].text
                                logging.debug("metric '{}' label '{}' - {} - {}: {}".format(metric_config['metric_name'], label_dict, tenant, namespace, node.text))
                                number = extract_number(node.text)
                                if number is not None:
                                    # Hard code check hard quota - Start
                                    if 'hardQuota' in metric_config['metric_path']:
                                        number = convert_hard_quota(node.text)
                                    # Hard code check hard quota - End
                                    self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + [tenant, namespace] + list(self.custom_labels.values()), number)
                                else:
                                    # Get non numeric data
                                    check_st = check_state(node.text)
                                    if check_st is not None:
                                        # Hard code for service state
                                        self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + [tenant, namespace] + list(self.custom_labels.values()), check_st)
                                    else:
                                        # Does not support the non numeric data
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
                    logging.debug("metric '{}' label '{}': {}".format(metric_config['metric_name'], label_dict, node.text))
                    number = extract_number(node.text)
                    if number is not None:
                        # Hard code check hard quota - Start
                        if 'hardQuota' in metric_config['metric_path']:
                            number = convert_hard_quota(node.text)
                        # Hard code check hard quota - End
                        self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + list(self.custom_labels.values()), number)
                    else:
                        # Get non numeric data
                        check_st = check_state(node.text)
                        if check_st is not None:
                            # Hard code for service state
                            self._prometheus_metrics[metric_config['metric_name']].add_metric(list(label_dict.values()) + list(self.custom_labels.values()), check_st)
                        else:
                            # Does not support the non numeric data
                            pass
    
    def collect(self):
        self._setup_empty_prometheus_metrics()
        self._collect_info_from_urls()
        try:
            self.populate_metrics()
        except Exception as err:
            logging.error("Error to populate metrics")
            logging.exception(err)
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
    REGISTRY.register(HCPCollector(config))
    while True:
        time.sleep(10)


if __name__ == "__main__":
    main()
