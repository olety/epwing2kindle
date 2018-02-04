#!/usr/bin/env python3
import pprint
import pandas as pd
import argparse
import logging
import json
import os
from tqdm import tqdm
from functools import partial
import sys


def process_folder(foldername):
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
        df.columns = ['word', 'reading', 'unk1',
                      'unk2', 'unk3', 'def', 'id', 'unk4']
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
        logging.debug('Transforming the definition into one string.')
        df['def'] = df['def'].apply(lambda x: ' '.join(x))
        logging.debug('Deleting duplicates.')
        df.drop_duplicates(inplace=True)
        logging.debug('Appending the dataframe to the result array.')
        result.append(df)

    # Concatenating the result and returning it
    logging.debug('Concatenating the result array.')
    result = pd.concat(result)
    logging.debug('Returning the result dataframe.')
    return result


if __name__ == '__main__':
    # Parsing the args
    parser = argparse.ArgumentParser(
        description='Converts EPWINGS dictionaries from yomichan zipped json '
        'into a tab-separated format that can be used with tab2opf.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Source files
    parser.add_argument(type=str, metavar='path', dest='folder',
                        help='Path to the unzipped yomichan-import '
                        'archive folder with json files.')

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

    # Starting processing
    logging.debug('Starting processing the source data...')
    result = process_folder(args.folder)

    result['def'] = result['def'].str.replace('\n', '\\n')
    # Saving the results
    logging.info(f'Saving the results to {args.output.name}...')
    result.to_csv(args.output, header=False, index=False, sep='\t',
                  encoding='utf-8', columns=['word', 'def'])
    logging.info(f'Successfully saved the results to {args.output.name}, '
                 'quitting the program.')
