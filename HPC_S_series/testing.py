import requests
import dicttoxml
import json
from pprint import pprint
from lxml import etree

headers = {
                    'Authorization': 'Basic YWRtaW46QWRtaW5AMTIz',
                    'X-HCPS-API-VERSION': '3.1.0'
                }
# result = requests.get(url= 'https://10.1.32.13:9090/mapi/system/status/full', headers=headers, verify=False)
# result = requests.get(url= 'https://10.1.32.13:9090/mapi/hardware', headers=headers, verify=False)
# data = json.loads(result.text)
with open('/home/kien/SVTECH/hitachi_prometheus_exporter/HPC_S_series/output_hcp_S31.txt', 'r') as f:
    data = json.load(f)
root = etree.fromstring(dicttoxml.dicttoxml(data))
tree = etree.ElementTree(root)
# for e in root.iter():
#     print(tree.getpath(e))
for leaf in tree.xpath('/root/serverModuleInfo/item/networkInterfaces/item/bond/error'):
    print("here")
    print(leaf.xpath("ancestor::item/id")[0].text)
    print(leaf.xpath("parent::bond/name")[0].text)
