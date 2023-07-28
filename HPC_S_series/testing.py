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
result = requests.get(url= 'https://10.1.32.13:9090/mapi/hardware', headers=headers, verify=False)
data = json.loads(result.text)
# pprint(data)
testfan1 = {
"actualFanSpeed": 6990,
"error": False,
"warning": False,
"off": False,
"actualSpeedCode": "LOWEST 1",
"id": 103,
"code": 1,
"location": "Fan 0A",
"swap": False,
"ident": False,
"fail": False
}
testfan2 = {
"actualFanSpeed": 9000,
"error": False,
"warning": False,
"off": False,
"actualSpeedCode": "HIGHEST 7",
"id": 104,
"code": 1,
"location": "Fan 0A",
"swap": False,
"ident": False,
"fail": False
}
data['enclosureInfo'][0]['fans'].append(testfan1)
data['enclosureInfo'][0]['fans'].append(testfan2)
# data['systemStatus']['hardware']['serverModuleInfo'] += data['systemStatus']['hardware']['serverModuleInfo']
# pprint(data['systemStatus']['hardware']['serverModuleInfo'])
# print(len(data['systemStatus']['hardware']['serverModuleInfo']))
# pprint(dicttoxml.dicttoxml(data))
root = etree.fromstring(dicttoxml.dicttoxml(data))
tree = etree.ElementTree(root)
# for e in root.iter():
#     print(tree.getpath(e))
for leaf in tree.xpath('/root/enclosureInfo/item/slots/item/state1'):
    print("here")
    print(type(leaf))
    print(leaf.xpath("ancestor::enclosureInfo/item/id")[0].text)
    print(leaf.xpath("parent::location")[0].text)
