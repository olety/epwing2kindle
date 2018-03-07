#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Script for converting an unzipped folder of yomichan json files into a
# Stardict tabfile. <word>\t<definition>
#
# (C) Oleksii Kyrylchuk 2018 (https://github.com/olety)
#
# Version history
# v0.1 (04.02.2018) Basic functionalities
# v0.2 (07.03.2018) Added proper katakana/kanji words processing, simplify mode
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

VERSION = '0.2'

import pprint
import pandas as pd
import argparse
import logging
import json
import os
from tqdm import tqdm
from functools import partial
from itertools import compress
import sys
import numpy as np


def clean_brackets(definition_list):
    return [defn.replace('【', ' 【')
            if len(defn.split(' 【')) == 1
            else defn
            for defn in definition_list]


def transform_simplify(definition_list):
    new_def = ''
    for definition in definition_list:
        defn = definition.split('\n')
        # Processing the header
        header = defn[0].split(' ')
        try:
            if header[1][0] == '―':
                header = [header[0]] + header[2:]
        except:
            pass
        defn[0] = ' '.join(header).replace('-', '')

        # Appending the definition
        new_def += '\n'.join(defn) + '\n'
    return new_def


def process_folder(foldername, simplify):
    logging.debug(f'Starting processing the folder {foldername}...')
    logging.debug('Initializing variables...')
    result = []
    to_process = [os.path.join(foldername, f)
                  for f in os.listdir(foldername)
                  if f.endswith('.json') and not f.startswith('index')]
    logging.debug('Files to process:')
    logging.debug(pprint.pformat(to_process))
    logging.debug('Starting the loop...')
    for file_path in tqdm(to_process, unit='file', desc='Processing files'):
        # Start and initializing
        logging.debug(f'Processing file {file_path}')

        logging.debug('Reading the json...')
        df = pd.read_json(file_path)
        logging.debug(f'Successfully read the file {file_path}...')

        logging.debug('Selecting the correct columns...')
        df.columns = ['word', 'reading', 'unknown1', 'unknown2',
                      'unknown3', 'def', 'id', 'unknown4']
        df = df[['word', 'reading', 'def']]
        logging.debug(f'Selected the columns {df.columns.values}...')

        # Hiragana-only words
        logging.debug('Starting processing the duplicate dataframe')
        logging.debug('This will allow us to look up words that are '
                      'spelled with hiragana and not kanji.')
        df_kanji = df[df['reading'].str.len() != 0]
        logging.debug('Copying the reading column to the key column')
        df_kanji.loc[:, 'word'] = df_kanji['reading']
        logging.debug('Concatenating the two dataframes, one for kanji words,'
                      'and the second one for hiragana words.')
        df = pd.concat([df, df_kanji]).sort_values(
            by='reading', ascending=False).reset_index(drop=True)

        # Transforming the def field + deleting dupes
        # Merging the definitions
        if simplify:
            logging.debug('Simplifying the definitions.')
            df['def'] = df['def'].apply(transform_simplify)
        else:
            logging.debug('Transforming the definition into one string.')
            df['def'] = df['def'].apply(lambda x: '\n'.join(x))
        # Making mixed kanji/kanakana words display properly
        df = df.apply(process_katakana_kanji, axis=1)
        df['word'] = df['word'].apply(clean_word_starts)
        # Deleting dupes
        logging.debug('Deleting duplicates.')
        df.drop_duplicates(inplace=True)
        logging.debug('Appending the dataframe to the result array.')
        result.append(df)

    # Concatenating the result and returning it
    logging.debug('Concatenating the result array.')
    result = pd.concat(result)
    # Some extra changes due to how tab2opf treats newlines
    logging.debug('Changing the newlines from \\n -> \\\\n '
                  'so tab2opf can read them.')
    result['def'] = result['def'].str.replace('\n', '\\n')
    # Maybe use a special sort for japanese characters?
    result = result.sort_values(by='word').reset_index()
    logging.debug('Returning the result dataframe.')
    return result


def clean_word_starts(word):
    # Ending words like -好き have a dash in the beginning
    # making them unsearcheable
    word = word.replace('…', '')
    if word.startswith('−'):
        word = word[1:]
    return word


def is_katakana(char):
    # https://en.wikipedia.org/wiki/Katakana_(Unicode_block)
    return ord('\u30ff') >= ord(char) >= ord('\u30a0')


def process_katakana_kanji(row):
    # Word structure: [Kanji/Hiragana]―[Kanji/Hiragana]
    # Reading structure: [Kanji/Hiragana]Katakana[Kanji/Hiragana]
    # ― is a special symbol (not dash -)
    # row[0] = word; row[1] = reading; row[2] = defn
    if '―' in row[0]:
        try:
            is_ktk = [is_katakana(character) for character in row[1]]
            # Finding the start/end of the katakana chunk
            # There should be a more efficient way to do this
            ktk_start = is_ktk.index(True)
            ktk_end = len(row[1]) - is_ktk[::-1].index(True)
            # Getting the leading/trailing kanji
            kanji = row[0].split('―')
            # Modifying the word itself by replacing hiragana with kanji
            row[0] = kanji[0] + row[1][ktk_start:ktk_end] + kanji[1]
        except:
            pass

    return row


if __name__ == '__main__':
    # Parsing the args
    parser = argparse.ArgumentParser(
        description='Converts EPWINGS dictionaries from yomichan zipped json '
        'into a tab-separated format that can be used with tab2opf. '
        'Version {VERSION}',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Source files
    parser.add_argument(type=str, metavar='path', dest='folder',
                        help='Path to the unzipped yomichan-import '
                        'archive folder with json files.')
    # Simplify defs
    parser.add_argument('-s', '--simplify', action='store_true',
                        help='Simplify definitions. This gets rid of the extra '
                        'archaic readings, which makes the resulting definition'
                        'easier to read.')
    # Destination
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), nargs='?',
                        metavar='output_tab', default='epwing.tab',
                        help='Output file path.')

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show verbose output.')
    # Parse the args
    args = parser.parse_args()

    # Setting up logging
    LOGGING_FMT = '%(levelname)s | %(asctime)s | line %(lineno)s | %(funcName)s | %(message)s'
    LOGGING_DATEFMT = '%H:%M:%S'

    logging_conf = partial(logging.basicConfig, format=LOGGING_FMT,
                           datefmt=LOGGING_DATEFMT, stream=sys.stdout)

    if args.verbose:
        logging_conf(level=logging.DEBUG)
    else:
        logging_conf(level=logging.INFO)

    # Setting pandas options so it won't throw warnings for no reason
    logging.debug('Setting pandas options...')
    pd.set_option('mode.chained_assignment', None)
    pd.set_option('max_colwidth', 100)  # for debug
    logging.debug('Finished setting pandas options.')

    # Processing
    logging.debug('Starting processing the source data...')
    result = process_folder(args.folder, simplify=args.simplify)
    logging.debug('Finished processing the source data...')

    # Saving the results
    logging.info(f'Saving the results to {args.output.name}...')
    result.to_csv(args.output, header=False, index=False, sep='\t',
                  encoding='utf-8', columns=['word', 'def'])
    logging.info(f'Successfully saved the results to {args.output.name}, '
                 'quitting the program.')
