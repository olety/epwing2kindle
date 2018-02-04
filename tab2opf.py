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
# Copyright (C) 2018 - Oleksii Kyrylchuk (github.com/olety)
#
# Version history:
# 0.1 (19.7.2007) Initial version
# 0.2 (2/2015) Rework removing encoding, runs on python3
# 0.2.1 (2/2018) Added progress bar, optimized for japanese.
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
VERSION = "0.2.1"

import sys
import os
import argparse
from itertools import islice, count, groupby
from contextlib import contextmanager
from tqdm import tqdm
import importlib

# Stop with the encoding -- it's broken anyhow
# in the kindles and undefined.


def normalizeLetter(ch):
    try:
        ch = mapping[ch]
    except KeyError:
        pass
    return ch


def normalizeUnicode(text):
    """
    Reduce some characters to something else
    """
    return ''.join(normalizeLetter(c) for c in text)

# Args:
#  --verbose
#  --module: module to load and attempt to extract getdef, getkey & mapping
#  --source: source language code (en by default)
#  --target: target language code (en by default)
#  file: the tab delimited file to read


def parseargs():
    parser = argparse.ArgumentParser(
        "tab2opf", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose", help="make verbose",
                        action="store_true")
    parser.add_argument("-m", "--module",
                        help="Import module for mapping, getkey, getdef")
    parser.add_argument("-s", "--source", default="ja", help="Source language")
    parser.add_argument("-t", "--target", default="ja", help="Target language")
    parser.add_argument("-o", "--output", default="opf", help="Target folder")
    parser.add_argument("file", help="tab file to input")
    return parser.parse_args()


def loadmember(mod, attr, dfault):
    if hasattr(mod, attr):
        print("Loading {} from {}".format(attr, mod.__name__))
        globals()[attr] = getattr(mod, attr)
    else:
        globals()[attr] = dfault


def importmod():
    global MODULE
    if MODULE is None:
        mod = None
    else:
        mod = importlib.import_module(MODULE)
        print("Loading methods from: {}".format(mod.__file__))

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

# add a single [term, definition]
# to defs[key]
# r is a tab split line


def readkey(r, defs):
    try:
        term, defn = r.split('\t', 1)
    except ValueError:
        print("Bad line: '{}'".format(r))
        raise

    term = term.strip()
    defn = getdef(defn)
    defn = defn.replace("\\\\", "\\").\
        replace(">", "&gt;").\
        replace("<", "&lt;").\
        replace("\\n", "<br/>\n").\
        strip()

    nkey = normalizeUnicode(term)
    key = getkey(nkey)
    key = key.\
        replace('"', "'").\
        replace('<', '&lt;').\
        replace('>', '&gt;').\
        lower().strip()

    nkey = nkey.\
        replace('"', "'").\
        replace('<', '&lt;').\
        replace('>', '&gt;').\
        lower().strip()

    if key == '':
        raise Exception("Missing key {}".format(term))
    if defn == '':
        raise Exception("Missing definition {}".format(term))

    if VERBOSE:
        print(key, ":", term)

    ndef = [term, defn, key == nkey]
    if key in defs:
        defs[key].append(ndef)
    else:
        defs[key] = [ndef]

# Skip empty lines and lines that only have a comment


def inclline(s):
    s = s.lstrip()
    return len(s) != 0 and s[0] != '#'

# Iterate over FILENAME, reading lines of
# term {tab} definition
# skips empty lines and commented out lines
#


def readkeys():
    if VERBOSE:
        print("Reading {}".format(FILENAME))
    with open(FILENAME, 'r', encoding='utf-8') as fr:
        defns = {}
        for r in tqdm(filter(inclline, fr), unit='keys', desc='Reading keys'):
            readkey(r, defns)
        return defns

# Write to key file {name}{n}.html
# put the body inside the context manager
# The onclick here gives a kindlegen warning
# but appears to be necessary to actually
# have a lookup dictionary


@contextmanager
def writekeyfile(name, i):
    fname = os.path.join(args.output, "{}{}.html".format(name, i))
    if VERBOSE:
        print("Key file: {}".format(fname))
    with open(fname, 'w') as to:
        to.write("""<?xml version="1.0" encoding="utf-8"?>
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
""")
        try:
            yield to
        finally:
            to.write("""
    </mbp:frameset>
  </body>
</html>
        """)

# Order definitions by keys, then by whether the key
# matches the original term, then by length of term
# then alphabetically


def keyf(defn):
    term = defn[0]
    if defn[2]:
        l = 0
    else:
        l = len(term)
    return l, term

# Write into to the key, definition pairs
# key -> [[term, defn, key==term]]


def writekey(to, key, defn):
    terms = iter(sorted(defn, key=keyf))
    for term, g in groupby(terms, key=lambda d: d[0]):
        to.write(
            """
      <idx:entry name="word" scriptable="yes">
        <h2>
          <idx:orth value="{key}">{term}</idx:orth>
        </h2>
""".format(term=term, key=key))

        to.write('; '.join(ndefn for _, ndefn, _ in g))
        to.write(
            """
      </idx:entry>
"""
        )

    if VERBOSE:
        print(key)

# Write all the keys, where defns is a map of
# key --> [[term, defn, key==term]...]
# and name is the basename
# The files are split so that there are no more than
# 10,000 keys written to each file (why?? I dunno)
#
# Returns the number of files.


def writekeys(defns, name):
    keyit = iter(sorted(defns))
    for j in tqdm(count(), unit='files', desc='Writing html'):
        with writekeyfile(name, j) as to:
            keys = list(islice(keyit, 10000))
            if len(keys) == 0:
                break
            for key in keys:
                writekey(to, key, defns[key])
    return j + 1

# After writing keys, the opf that references all the key files
# is constructed.
# openopf wraps the contents of writeopf
#


@contextmanager
def openopf(ndicts, name):
    fname = os.path.join(args.output, "{}.opf".format(name))
    if VERBOSE:
        print("Opf: {}".format(fname))
    with open(fname, 'w') as to:
        to.write("""<?xml version="1.0"?><!DOCTYPE package SYSTEM "oeb1.ent">

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
""".format(name=name, source=INLANG, target=OUTLANG))

        yield to

        to.write("""
<tours/>
<guide> <reference type="search" title="Dictionary Search" onclick= "index_search()"/> </guide>
</package>
"""
                 )

# Write the opf that describes all the key files


def writeopf(ndicts, name):
    with openopf(ndicts, name) as to:
        for i in range(ndicts):
            to.write(
                """     <item id="dictionary{ndict}" href="{name}{ndict}.html" media-type="text/x-oeb1-document"/>
""".format(ndict=i, name=name))

        to.write("""
</manifest>
<!-- list of the html files in the correct order  -->
<spine>
"""
                 )
        for i in range(ndicts):
            to.write("""
	<itemref idref="dictionary{ndict}"/>
""".format(ndict=i))

        to.write("""
</spine>
""")

######################################################
# main
######################################################


defns = readkeys()
name = os.path.splitext(os.path.basename(FILENAME))[0]
ndicts = writekeys(defns, name)
print("Writing opf")
writeopf(ndicts, name)
