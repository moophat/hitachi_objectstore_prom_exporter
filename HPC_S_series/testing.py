import requests
import dicttoxml
import json
from pprint import pprint
from lxml import etree

headers = {
                    'Authorization': 'Basic YWRtaW46U3RhcnQxMjMh',
                    'X-HCPS-API-VERSION': '3.1.0'
                }
# result = requests.get(url= 'https://10.1.22.167:9090/mapi/system/status/full', headers=headers, verify=False)
result = requests.get(url= 'https://10.1.22.167:9090/mapi/metrics/system', headers=headers, verify=False)
data = json.loads(result.text)
# pprint(data)
# data['systemStatus']['hardware']['serverModuleInfo'] += data['systemStatus']['hardware']['serverModuleInfo']
# pprint(data['systemStatus']['hardware']['serverModuleInfo'])
# print(len(data['systemStatus']['hardware']['serverModuleInfo']))
# pprint(dicttoxml.dicttoxml(data))
root = etree.fromstring(dicttoxml.dicttoxml(data))
tree = etree.ElementTree(root)
for e in root.iter():
    print(tree.getpath(e))