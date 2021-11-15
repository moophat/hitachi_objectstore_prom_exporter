import requests
from pprint import pprint
from lxml import etree


headers = {
    'Authorization': 'HCP YWRtaW4=:0e7517141fb53f21ee439b355b5a1d0a',
    'Accept': 'application/xml'
}

# url = 'https://10.1.22.163:9090/mapi/nodes/statistics'
# url = 'https://10.1.22.163:9090/mapi/tenants/sonvuduc'
# url = 'https://10.1.22.163:9090/mapi/tenants/sonvuduc/statistics'
url = 'https://10.1.22.163:9090/mapi/services/statistics'
result = requests.get(url=url, headers=headers, verify=False)
root = etree.fromstring(result.content)
tree = etree.ElementTree(root)
for e in root.iter():
    print(tree.getpath(e))
# print(result.content)
# node = tree.xpath('/nodeStatistics/nodes/node/volumes/volume/blocksWritten')[7]
# for i in range(len(tree.xpath('/nodeStatistics/nodes/node/volumes/volume/blocksWritten'))):
#     node = tree.xpath('/nodeStatistics/nodes/node/volumes/volume/blocksWritten')[i]
#     print('current node:')
#     print(node.text)
#     print('label IP:')
#     parent = node.xpath('ancestor::node/backendIpAddress')
#     print(parent[0].tag, parent[0].text)
#     print('volume id:')
#     id = node.xpath('ancestor::volume/id')
#     print(id[0].tag, id[0].text)
# parent = node.xpath('ancestor::node/backendIpAddress')
# print(parent[0].tag, parent[0].text)