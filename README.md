# Convert EPWING dictionaries to a kindle-readable format (Japanese)

<img src="images/demo.jpeg" alt="Result demonstration" style="width: 300px; display: block;"/>

*Demonstration of the final result*

## Process description

![Process flowchart](images/flowchart.svg)

In order to convert an EPWING dictionary to kindle, you first have to follow the process displayed above: first you convert the EPWING to a stardict format (TAB-separated), then using tab2opf you can convert it to opf (html) dictionary and then generate a mobi file using kindlegen.

*Note*: this process was tested using 大辞林三省堂, using it with other dictionaries like 新明解国語辞典 should still work but some unexpected problems may arise. 

## Usage

### Requirements: 

- [python 3.6 or higher](https://www.python.org/)
- [yomichan-import](https://foosoft.net/projects/yomichan-import/)
- [kindlegen](https://www.amazon.com/gp/feature.html?docId=1000765211)
- `pip3 install -r requirements.txt` for python requirements

### EPWING to JSON (yomichan)

```
./yomichan-import
```

### JSON to Tab (yomi2tab)

```
pip3 install -r requirements.txt
python3 yomi2tab.py -o dict.tab data
```

Yomichan-import generates an archive file, that you have to unzip into a folder (called `data` in the above example) for `yomi2tab` to work.

### Tab to OPF (tab2opf)

This repository provides a japanese-specific tab2opf tool with some improvements (adding progress indicators, correct display of `<`/`>`, etc.). It is based on https://github.com/apeyser/tab2opf by Alexander Peyser from 2015 which itself is based on the generally available tab2opf.py by Klokan Petr Přidal (www.klokan.cz) from 2007.

```
python3 tab2opf.py dict.tab
```

## OPF to mobi (kindlegen)

```
kindlegen opf/dict.opf
```

In order to generate a .mobi dictionary from OPF, you can use a tool called `kindlegen` that's provided by amazon. It may take a while but doesn't require any extra work.

After you've generated a .mobi dictionary, you can import it into [calibre](https://calibre-ebook.com) to edit the metadata, add the cover picture and send it to kindle.

## Miscellaneous

### Another way to convert epwing

We can also use the noj format as an intermediary between the EPWING dictionary and the tab file. 

**Steps:**

1. https://github.com/mcho421/noj_dumpers
	
	*  Don't bother with compiling it because won't work, just copy your files to the noj_dumper folder and then `python2 noj_dumper.py epwing_folder`
2. https://github.com/asika/noj2tab (you can try reading the Chinese blog post with google translate)
3. Tab2Opf (mine or https://github.com/apeyser/tab2opf)
4. kindlegen + calibre

### Why would you ever do this? Kindle offers free builtin dictionaries!

デジタル大辞泉　provided with Kindle doesn't have pitch accent marks.

### Shoutouts

Cophnia61 - https://forum.koohii.com/thread-14949.html

### IS THE PICTURE A ... REFERENCE????

Yes ;)
