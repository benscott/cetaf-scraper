#!/usr/bin/env python
# encoding: utf-8
"""
Created by Ben Scott on '07/03/2017'.
"""

import csv
# import unicodecsv as csv
import click
import requests
from bs4 import BeautifulSoup
import requests_cache
from collections import OrderedDict


DOMAIN = 'http://cetaf.org'
INDEX_PAGE = 'http://cetaf.org/services/institutional-profiles'


requests_cache.install_cache('.cetaf_cache')


def get_url_as_soup(url):
    r = requests.get(url)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")


def list_institutions():
    soup = get_url_as_soup(INDEX_PAGE)
    section = soup.find("section", {"id": "block-views-passports-per-countries-block"})
    institution_links = section.find_all("a")
    for institution_link in institution_links:
        yield institution_link.text, institution_link['href']

@click.command()
@click.option('--limit', default=None, help='Number of institutions to process.', type=click.FLOAT)
def main(limit):

    rows = []

    for i, (institution, href) in enumerate(list_institutions()):
        if i == limit:
            break
        print('Parsing: ', institution)
        institution_page = '{0}{1}'.format(DOMAIN, href)
        soup = get_url_as_soup(institution_page)

        zone_fields = soup.find("div", {"id": "zone_fields"})

        sections = zone_fields.find_all("div", {"class": "tabcontent"})

        parsed_data = OrderedDict([('Institution', institution)])

        for section in sections:

            # print(section['id'])

            fields = section.find_all("div", {"class": "field"})
            for field in fields:
                # If this is indented content, see if there's additional field label info
                field_label = field.find("div", {"class": "field-label"})

                label_parts = []

                parent_field = field.find_parent("div", {"class": "field"})
                if parent_field:
                    parent_field_label = parent_field.find("div", {"class": "field-label"}, recursive=False)
                    label_parts.append(parent_field_label.text.strip())

                if 'content_indent' in field.parent["class"]:
                    group_label = field.parent.find("div", {"class": "content_group_label_3"})
                    if group_label and group_label.text.lower().strip() != label.lower().strip():
                        label_parts.append(group_label.text.strip().title())

                try:
                    label_parts.append(field_label.text.replace('\xa0', ''))
                except AttributeError:
                    print('No label for %s - %s' % (institution, field_label))
                    continue

                label = ' - '.join(label_parts)

                field_items = field.find_all("div", {"class": "field-item"})

                for field_item in field_items:

                    field_item_content = field_item.next

                    if field_item_content.name == 'a':
                        value = field_item_content['href']
                    elif field_item_content.name == 'p':
                        value = field_item_content.text
                    elif field_item_content.name in [None, 'img']:
                        value = field_item_content
                    else:
                        continue

                    if label == 'Institution (Original name)':
                        continue

                    if label in parsed_data:
                        try:
                            parsed_data[label].append(value)
                        except AttributeError:
                            parsed_data[label] = [parsed_data[label], value]
                    else:
                        parsed_data[label] = value

        rows.append(parsed_data)

    # Build headers
    headers = []
    for row in rows:
        headers += [f for f in row.keys() if f not in headers]

    with open('cetaf-institutions.csv', 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()