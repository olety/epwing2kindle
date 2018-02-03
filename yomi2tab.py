import json
from pprint import pprint
import pandas as pd
import os


def test():
    test = df[df['reading'].str.contains('せりふづくし')]
    print(len(test))


# Options
pd.set_option('mode.chained_assignment', None)
pd.set_option('max_colwidth', 100)

# TODO: iterate
current_tb = f'data/term_bank_16.json'


df = pd.read_json(current_tb)

df.columns = ['word', 'reading', 'unk1', 'unk2', 'unk3', 'def', 'id', 'unk4']
df = df[['word', 'reading', 'def']]
test()

df_kanji = df[df['reading'].str.len() != 0]
df_kanji.loc[:, 'word'] = df_kanji['reading']

df = pd.concat([df, df_kanji]).sort_values(
    by='reading', ascending=False).reset_index(drop=True)


df['def'] = df['def'].apply(lambda x: ' '.join(x))

test()
df.drop_duplicates(inplace=True)
test()

df.to_csv('test.csv', header=False, sep='\t', encoding='utf-16')
