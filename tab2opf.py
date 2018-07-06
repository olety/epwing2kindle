#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Script for conversion of Stardict tabfile (<header>\t<definition>
# per line) into the OPF file for MobiPocket Dictionary
#
# For usage of dictionary convert it by:
# (wine) mobigen.exe DICTIONARY.opf
# or now...
# kindlegen DICTIONARY.opf
#
# MobiPocket Reader at: www.mobipocket.com for platforms:
#   PalmOs, Windows Mobile, Symbian (Series 60, Series 80, 90, UIQ), Psion, Blackberry, Franklin, iLiad (by iRex), BenQ-Siemens, Pepper Pad..
#   http://www.mobipocket.com/en/DownloadSoft/DownloadManualInstall.asp
# mobigen.exe available at:
#   http://www.mobipocket.com/soft/prcgen/mobigen.zip
#
# Copyright (C) 2007 - Klokan Petr Přidal (www.klokan.cz)
# Copyright (C) 2015 - Alexander Peyser (github.com/apeyser)
# Copyright (C) 2018 - Oleksii Kyrylchuk (https://github.com/olety)
#
# Version history:
# 0.1 (19.7.2007) Initial version
# 0.2 (2/2015) Rework removing encoding, runs on python3
# 0.2.1 (2/2018) Added progress bar, optimized for japanese.
# 0.2.2 (3/2018) Added docstrings, proper multiple definitions, f-strings, "->'
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
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

# VERSION
VERSION = "0.2.2"

import sys
import os
import argparse
from itertools import islice, count, groupby
from contextlib import contextmanager
from tqdm import tqdm
import importlib


def normalizeLetter(ch):
    # Stop with the encoding -- it's broken anyhow
    # in the kindles and undefined.
    try:
        ch = mapping[ch]
    except KeyError:
        pass
    return ch


def normalizeUnicode(text):
    '''
    Reduce some characters to something else
    '''
    return ''.join(normalizeLetter(c) for c in text)


def parseargs():
    # Args:
    #  --verbose
    #  --module: module to load and attempt to extract getdef, getkey & mapping
    #  --source: source language code (en by default)
    #  --target: target language code (en by default)
    #  file: the tab delimited file to read
    parser = argparse.ArgumentParser(
        'tab2opf', formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=f'Tab2Opf [v{VERSION}] Converts dictionaries from a '
        'tab-separated Stardict format into OPF/html format that can be '
        'further be converted to MOBI with kindlegen. Made by '
        'Klokan Petr Přidal, Alexander Peyser, Oleksii Kyrylchuk.')
    parser.add_argument('-v', '--verbose', help='make verbose',
                        action='store_true')
    parser.add_argument('-m', '--module',
                        help='Import module for mapping, getkey, getdef')
    parser.add_argument('-s', '--source', default='ja', help='Source language')
    parser.add_argument('-t', '--target', default='ja', help='Target language')
    parser.add_argument('-o', '--output', default='opf', help='Target folder')
    parser.add_argument('file', help='tab file to input')
    return parser.parse_args()


def loadmember(mod, attr, dfault):
    if hasattr(mod, attr):
        print(f'Loading {attr} from {mod.__name__}')
        globals()[attr] = getattr(mod, attr)
    else:
        globals()[attr] = dfault


def importmod():
    global MODULE
    if MODULE is None:
        mod = None
    else:
        mod = importlib.import_module(MODULE)
        print(f'Loading methods from: {mod.__file__}')

    loadmember(mod, 'getkey', lambda key: key)
    loadmember(mod, 'getdef', lambda dfn: dfn)
    loadmember(mod, 'mapping', {})


args = parseargs()
if not os.path.exists(args.output):
    os.makedirs(args.output)
VERBOSE = args.verbose
FILENAME = args.file
MODULE = args.module
INLANG = args.source
OUTLANG = args.target
importmod()


def readkey(line, defs):
    '''
    Add a single [term, definition] to the defs[key] dictionary.
    line is a tab split line to be parsed.
    '''
    try:
        term, defn = line.split('\t', 1)
    except ValueError:
        print('Bad line: "{}"'.format(line))
        raise

    term = term.strip()
    defn = getdef(defn)
    newl = '<br/>\n'
    tab = '&emsp;'
    defn = defn.replace('\\\\', '\\').\
        replace('"', '\'').\
        replace('>', '&gt; ').\
        replace('<', ' &lt;').\
        replace('（ア）', f'{newl}{tab}（ア）').\
        replace('（イ）', f'{newl}{tab}（イ）').\
        replace('（ウ）', f'{newl}{tab}（ウ）').\
        replace('（エ）', f'{newl}{tab}（エ）').\
        replace('（オ）', f'{newl}{tab}（オ）').\
        replace('\\n', newl).\
        strip()

    nkey = normalizeUnicode(term)
    key = getkey(nkey)
    key = key.\
        replace('"', '\'').\
        replace('<', '&lt;').\
        replace('>', '&gt;').\
        lower().strip()

    nkey = nkey.\
        replace('"', '\'').\
        replace('<', '&lt;').\
        replace('>', '&gt;').\
        lower().strip()

    if key == '':
        raise Exception(f'Missing key {term}')
    if defn == '':
        raise Exception(f'Missing definition {term}')

    if VERBOSE:
        print(key, ':', term)

    ndef = [term, defn, key == nkey]
    if key in defs:
        defs[key].append(ndef)
    else:
        defs[key] = [ndef]


def inclline(s):
    ''' Filter that skips empty lines and lines that only have a comment '''
    s = s.lstrip()
    return len(s) != 0 and s[0] != '#'


def readkeys():
    '''
    Iterate over FILENAME, reading lines formatted like "term {tab} definition".
    Skips empty lines and commented out lines.
    '''
    if VERBOSE:
        print('Reading {}'.format(FILENAME))
    with open(FILENAME, 'r', encoding='utf-8') as fr:
        defs = {}

        for line in tqdm(filter(inclline, fr), unit='keys', desc='Reading keys'):
            readkey(line, defs)
        return defs


@contextmanager
def writekeyfile(name, i):
    '''
    Write to key file '{name}{n}.html', put the body inside the context manager.
    The onclick here gives a kindlegen warning but appears to be necessary to
    actually have a lookup dictionary
    '''
    fname = os.path.join(args.output, f'{name}{i}.html')
    if VERBOSE:
        print('Key file: {}'.format(fname))
    with open(fname, 'w', encoding='utf-8') as to:
        to.write('''<?xml version="1.0" encoding="utf-8"?>
<html xmlns:idx="www.mobipocket.com" xmlns:mbp="www.mobipocket.com" xmlns:xlink="http://www.w3.org/1999/xlink">
  <body>
    <mbp:pagebreak/>
    <mbp:frameset>
      <mbp:slave-frame display="bottom" device="all" breadth="auto" leftmargin="0" rightmargin="0" bottommargin="0" topmargin="0">
        <div align="center" bgcolor="yellow"/>
        <a onclick="index_search()">Dictionary Search</a>
        </div>
      </mbp:slave-frame>
      <mbp:pagebreak/>
''')
        try:
            yield to
        finally:
            to.write('''
    </mbp:frameset>
  </body>
</html>
        ''')


def keyf(defn):
    '''
    Order definitions by keys, then by whether the key matches the original
    term, then by length of term then alphabetically.
    '''
    term = defn[0]
    if defn[2]:
        l = 0
    else:
        l = len(term)
    return l, term


def writekey(to, key, defn):
    '''
    Write into to the key, definition pairs
        key -> [[term, defn, key==term]]
    '''
    terms = iter(sorted(defn, key=keyf))
    for term, g in groupby(terms, key=lambda d: d[0]):
        for thing in g:
            to.write(
                '''
                      <idx:entry name="word" scriptable="yes">
                        <h2>
                          <idx:orth value="{key}">{term}</idx:orth>
                        </h2>
                '''.format(term=term, key=key))
            # Merge definitions; Added sorting to display japanese results first
            # defn = '<br/><hr>'.join(sorted(ndefn for _, ndefn, _ in g))
            # Fixing the reading error where english definitions
            # generate extra spacing
            # defn.replace('<br/>\n<br/><hr>', '<br/><hr>')
            to.write(thing[1])
            to.write('''
                </idx:entry>
            ''')

    if VERBOSE:
        print(key)


def writekeys(defns, name):
    '''
    Write all the keys, where defns is a map of
        key --> [[term, defn, key==term]...]
    and name is the basename.

    The files are split so that there are no more than 10,000 keys written
    to each file. (why?? I dunno. Probably to reduce lag when opening them.)

    Returns the number of files.
    '''
    keyit = iter(sorted(defns))
    for j in tqdm(count(), unit='files', desc='Writing html'):
        with writekeyfile(name, j) as to:
            keys = list(islice(keyit, 10000))
            if len(keys) == 0:
                break
            for key in keys:
                writekey(to, key, defns[key])
    return j + 1


@contextmanager
def openopf(ndicts, name):
    '''
    After writing keys, the opf that references all the key files is constructed.
    openopf wraps the contents of writeopf
    '''
    fname = os.path.join(args.output, f'{name}.opf')
    if VERBOSE:
        print(f'Opf: {fname}')
    with open(fname, 'w', encoding='utf-8') as to:
        to.write('''<?xml version="1.0"?><!DOCTYPE package SYSTEM "oeb1.ent">

<!-- the command line instruction 'prcgen dictionary.opf' will produce the dictionary.prc file in the same folder-->
<!-- the command line instruction 'mobigen dictionary.opf' will produce the dictionary.mobi file in the same folder-->

<package unique-identifier="uid" xmlns:dc="Dublin Core">

<metadata>
	<dc-metadata>
		<dc:Identifier id="uid">{name}</dc:Identifier>
		<!-- Title of the document -->
		<dc:Title><h2>{name}</h2></dc:Title>
		<dc:Language>ja</dc:Language>
	</dc-metadata>
	<x-metadata>
	        <output encoding="utf-8" flatten-dynamic-dir="yes"/>
		<DictionaryInLanguage>{source}</DictionaryInLanguage>
		<DictionaryOutLanguage>{target}</DictionaryOutLanguage>
	</x-metadata>
</metadata>

<!-- list of all the files needed to produce the .prc file -->
<manifest>
'''.format(name=name, source=INLANG, target=OUTLANG))

        yield to

        to.write('''
<tours/>
<guide> <reference type="search" title="Dictionary Search" onclick= "index_search()"/> </guide>
</package>
'''
                 )

# Write the opf that describes all the key files


def writeopf(ndicts, name):
    with openopf(ndicts, name) as to:
        for i in range(ndicts):
            to.write(
                '''     <item id="dictionary{ndict}" href="{name}{ndict}.html" media-type="text/x-oeb1-document"/>
'''.format(ndict=i, name=name))

        to.write('''
</manifest>
<!-- list of the html files in the correct order  -->
<spine>
'''
                 )
        for i in range(ndicts):
            to.write('''
	<itemref idref="dictionary{ndict}"/>
'''.format(ndict=i))

        to.write('''
</spine>
''')

######################################################
# main
######################################################


defns = readkeys()
name = os.path.splitext(os.path.basename(FILENAME))[0]
ndicts = writekeys(defns, name)
print('Writing opf:')
writeopf(ndicts, name)
