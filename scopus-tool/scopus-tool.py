from elsapy.elsclient import ElsClient
from elsapy.elsprofile import ElsAuthor
from elsapy.elssearch import ElsSearch
import numpy as np
import json
import os
import datetime

def h_index(citations):
    citations = np.array(citations)
    n = citations.shape[0]
    array = np.arange(1, n+1)
    citations = np.sort(citations)[::-1]
    h_idx = np.max(np.minimum(citations, array))
    return h_idx

dir_path = os.path.dirname(os.path.realpath(__file__))

con_file = open(dir_path + "/config.json")
config = json.load(con_file)
con_file.close()

client = ElsClient(config['apikey'])
client.inst_token = config['insttoken']


author_input = input('insert author (name surname) ---> ')
name, surname = author_input.split(' ')
print('_________________________________________________')
auth_srch = ElsSearch('authfirst({}) AND authlast({})'.format(name, surname), 'author')
auth_srch.execute(client)
print("author search has", len(auth_srch.results), "results:")
print('_________________________________________________')
for i, result in enumerate(auth_srch.results):
    affiliation = result["affiliation-current"]["affiliation-name"]
    orcid = result['orcid'] if 'orcid' in result else 'No ORCID'
    total_doc = result['document-count']
    link = result['link'][3]['@href']
    print("{} - affiliation: {}, ORCID: {}, total papers: {}".format(i, affiliation, orcid, total_doc))
    print("link: {}".format(link))
    print('_________________________________________________')

selected_author = None
if len(auth_srch.results) > 1:
    while selected_author is None or selected_author not in range(len(auth_srch.results)):
        try:
            selected_author = int(input("multiple authors found. Select author ---> "))
        except ValueError:
            print("insert a number")
else:
    selected_author = 0

author = ElsAuthor(uri = auth_srch.results[selected_author]['link'][0]['@href'])
if author.read(client):
    print("author loaded")
else:
    print("read author failed.")



years_input = input('''
insert years range:
all
last 5
last 10
START_YEAR END_YEAR
YEAR
---> ''')
start = 1
end = datetime.datetime.now().year

if years_input == 'last 5':
    start = end - 4
elif years_input == 'last 10':
    start = end - 9
elif ' ' in years_input:
    try:
        start, end = years_input.split(' ')
        start = int(start)
        end = int(end)
    except:
        print('invalid range')
elif years_input.isdigit():
    start = int(years_input)
    end = int(years_input)
else:
    print('invalid input, using default (all)')

print('_________________________________________________')





print("loading papers...")
author_id = author.id.split(':')[1]
start -= 1
end += 1
doc_srch = ElsSearch("AU-ID({}) AND PUBYEAR > {} AND PUBYEAR < {}".format(author_id, start, end),'scopus')
doc_srch.execute(client, get_all = True)
print ("document search has", len(doc_srch.results), "papers")
print('#################################################')
print('#################################################')
print('Statistics of {} from year {} to {}'.format(author.full_name, start+1, end-1))
pub_num = len(doc_srch.results)
journal_pub = 0
total_citedby = 0
citations = []
for result in doc_srch.results:
    journal_pub += 1 if 'Article' in result['subtypeDescription'] else 0
    total_citedby += int(result['citedby-count'])
    citations.append(int(result['citedby-count']))
hindex = h_index(citations)
print("Publications: {}, in Journal: {}, cited by: {}, hindex: {}".format(pub_num, journal_pub, total_citedby, hindex))
print('#################################################')
print('#################################################')
print('show paper details?')
input_paper = input('Y/n ---> ')
if input_paper == 'y' or input_paper == '' or input_paper == 'Y':
    for result in doc_srch.results:
        print("{}\n cited by: {}, #authors: {}, Field-Weighted citation impact: {}\n".format(
            result['dc:title'], result['citedby-count'], 0,0))



