from elsapy.elsclient import ElsClient
from elsapy.elsprofile import ElsAuthor
from elsapy.elssearch import ElsSearch

from bs4 import BeautifulSoup
import requests

import numpy as np
import json
import os
import datetime

VALID_CATEGORIES = [
    "Multidisciplinary",

    "Artificial Intelligence", "Computational Theory and Mathematics", "Computer Graphics and Computer-Aided Design", "Computer Networks and Communications", "Computer Science Applications", "Computer Science (miscellaneous)", "Computer Vision and Pattern Recognition", "Hardware and Architecture", "Human-Computer Interaction", "Information Systems", "Signal Processing", "Software"

    "Control and Systems Engineering", "Electrical and Electronic Engineering"
]

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

auth_srch = None
while auth_srch is None:
    author_input = input('insert author (name surname) ---> ')
    if ' ' in author_input:
        name, surname = author_input.split(' ')
    else:
        print('insert name and surname')
        continue
    print('_________________________________________________')
    auth_srch = ElsSearch('authfirst({}) AND authlast({})'.format(name, surname), 'author')
    auth_srch.execute(client)
    if 'error' in auth_srch.results[0]:
        print('author not found, error: {}'.format(auth_srch.results[0]['error']))
        auth_srch = None

print("author search has", len(auth_srch.results), "results:")
print('_________________________________________________')
for i, result in enumerate(auth_srch.results):
    affiliation = result["affiliation-current"]["affiliation-name"] if 'affiliation-current' in result else None
    orcid = result['orcid'] if 'orcid' in result else None
    total_doc = result['document-count'] if 'document-count' in result else None
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
        paper_id = result['dc:identifier'].split(':')[1]
        auth_count_response = client.exec_request("https://api.elsevier.com/analytics/scival/publication/metrics?metricTypes=AuthorCount&publicationIds={}&byYear=false&includedDocs=AllPublicationTypes".format(paper_id))
        auth_count = int(auth_count_response["results"][0]["metrics"][0]["value"]) if 'value' in auth_count_response["results"][0]["metrics"][0] else 0
        fwci_response = client.exec_request("https://api.elsevier.com/analytics/scival/publication/metrics?metricTypes=FieldWeightedCitationImpact&publicationIds={}&byYear=false&includedDocs=AllPublicationTypes".format(paper_id))
        fwci = int(fwci_response["results"][0]["metrics"][0]["value"]) if 'value' in fwci_response["results"][0]["metrics"][0] else 0

        quartile = None
        if 'Article' in result['subtypeDescription']:
            scimago_search_page = requests.get("https://www.scimagojr.com/journalsearch.php?q={}".format(result["prism:publicationName"]))
            parsed_search_page = BeautifulSoup(scimago_search_page.text, "html.parser")
            links = parsed_search_page.find_all('a')
            scimago_link = None
            for link in links:
                if result["prism:publicationName"] in link.text:
                    scimago_link = link['href']
                    break
            if scimago_link is not None:
                scimago_j_page = requests.get("https://www.scimagojr.com/" + scimago_link)
                parsed_j_page = BeautifulSoup(scimago_j_page.text, "html.parser")
                tables = parsed_j_page.find_all('table')
                quartile_table = None
                for table in tables:
                    if 'Quartile' in table.text:
                        quartile_table = table
                        break
                if quartile_table is not None:
                    body = quartile_table.contents[1]
                    for child in body.contents:
                        if (len(child.text) > 6 and
                            fwci_response["results"][0]["publication"]["publicationYear"] == int(child.text[-6:-2]) and
                            child.text[:-6] in VALID_CATEGORIES):
                                categoty_quartile = int(child.text[-1])
                                if quartile is None or categoty_quartile < quartile:
                                    quartile = categoty_quartile
                                
        print("{}\n cited by: {}, #authors: {}, Field-Weighted citation impact: {}, Quartile: {}\n".format(
            result['dc:title'], result['citedby-count'], auth_count, fwci, quartile))



