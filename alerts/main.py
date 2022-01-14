import urllib3
import time
import os
import logging
import yaml
from yaml.scanner import ScannerError
import requests
import json
from pprint import pprint
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


CONFIG_FILE = "config.yml"
LOG_FILE = '/var/log/HPC_alerts.log'
config = {}


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


def main():
    global config
    config = load_config()
    if config.get('log_file'):
        log_file = config['log_file']
    else:
        log_file = LOG_FILE
    config_logging(log_file)
    while True:
        alerts = []
        for node in config['snodes']:
            headers = {
                'Authorization': node['Authorization'],
                'X-HCPS-API-VERSION': '3.1.0'
            }
            result = requests.get(url=node['base_url'] + '/mapi/alerts', headers=headers, verify=False)
            data = json.loads(result.text)['alerts']
            for alert in data:
                alert['alertname'] = alert.pop('shortName')
                alert.pop('ticket')
                alert['scopeRef'] = str(alert['scopeRef'])
                alert['instance'] = node['node_name']
                alerts.append({"labels": alert, "annotations": {"summary": "Alert from " + node['node_name']}, "generatorURL": node['more_info']})
        if len(alerts) > 0:
            try:
                response = requests.post(config['alert_manager'], json=alerts)
                print("Send to alertmanager")
                if response.status_code != 200:
                    logging.error("The request is failed!")
            except Exception as err:
                logging.error("Can't send the alerts to the alertmanager")
                logging.exception(err)
        else:
            logging.debug("System has no alert")
        time.sleep(int(config.get('interval')))


if __name__ == "__main__":
    main()
